from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.contrib.admin.options import IS_POPUP_VAR
from django.core.exceptions import ImproperlyConfigured
from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext_lazy as _

from djangocms_picture.backends.base import (
    BaseImageAsset,
    BasePictureBackend,
    PictureBackendError,
)
from djangocms_picture.backends.types import (
    BackendCapabilities,
    ImageAttribution,
    ImageInfo,
    PictureReference,
    Rendition,
    RenditionSpec,
)

from .data import UNSPLASH_OUTPUT_FORMATS, normalize_unsplash_payload
from .forms import UnsplashImageChoiceField

UNSPLASH_FORMATS = tuple(sorted(UNSPLASH_OUTPUT_FORMATS - {""}))
UNSPLASH_COLORS = frozenset(
    {
        "",
        "black_and_white",
        "black",
        "white",
        "yellow",
        "orange",
        "red",
        "purple",
        "magenta",
        "green",
        "teal",
        "blue",
    }
)
UNSPLASH_CAPABILITIES = BackendCapabilities(
    resize=True,
    crop=True,
    upscale=True,
    responsive=True,
    remote=True,
    permanent_urls=True,
    formats=UNSPLASH_FORMATS,
)


class UnsplashImageAsset(BaseImageAsset):
    capabilities = UNSPLASH_CAPABILITIES

    def __init__(self, reference: PictureReference) -> None:
        self.reference = reference
        snapshot = reference.snapshot
        self.info = ImageInfo(
            label=str(snapshot.get("label") or reference.id),
            width=snapshot.get("width"),
            height=snapshot.get("height"),
            alt_text=str(snapshot.get("alt_text") or ""),
        )
        self.attribution = ImageAttribution.from_mapping(snapshot.get("attribution"))

    def get_original(self) -> Rendition:
        transform = self.reference.snapshot.get("transform", {})
        params = _output_params(transform)
        return Rendition(
            url=(
                _replace_image_query(str(self.reference.snapshot["raw_url"]), params)
                if params
                else str(self.reference.snapshot["full_url"])
            ),
            width=self.info.width,
            height=self.info.height,
        )

    def get_rendition(self, spec: RenditionSpec) -> Rendition:
        transform = self.reference.snapshot.get("transform", {})
        output_format = spec.format or transform.get("format")
        quality = spec.quality if spec.quality is not None else transform.get("quality")
        if output_format and output_format not in UNSPLASH_FORMATS:
            raise PictureBackendError(f'Unsplash does not support the "{output_format}" format.')
        if quality is not None and not 0 <= quality <= 100:
            raise PictureBackendError("Unsplash rendition quality must be between 0 and 100.")

        width, height = self._rendition_dimensions(spec)
        params: dict[str, str | int] = {}
        if width:
            params["w"] = width
        if height:
            params["h"] = height
        if spec.crop and width and height:
            crop_mode = str(transform.get("crop_mode") or "entropy")
            params.update({"fit": "crop", "crop": crop_mode})
            if crop_mode == "focalpoint":
                focal_point = transform.get("focal_point", {})
                params["fp-x"] = str(focal_point.get("x", 0.5))
                params["fp-y"] = str(focal_point.get("y", 0.5))
        elif width or height:
            params["fit"] = "max"
        if output_format:
            params["fm"] = output_format
        if quality is not None:
            params["q"] = quality

        return Rendition(
            url=_replace_image_query(str(self.reference.snapshot["raw_url"]), params),
            width=width,
            height=height,
        )

    def _rendition_dimensions(self, spec: RenditionSpec) -> tuple[int | None, int | None]:
        source_width, source_height = self.info.width, self.info.height
        if not source_width or not source_height:
            return spec.width, spec.height

        if spec.crop and spec.width and spec.height:
            scale = 1.0
            if not spec.upscale:
                scale = min(1.0, source_width / spec.width, source_height / spec.height)
            return round(spec.width * scale), round(spec.height * scale)

        if spec.width and spec.height:
            scale = min(spec.width / source_width, spec.height / source_height)
        elif spec.width:
            scale = spec.width / source_width
        elif spec.height:
            scale = spec.height / source_height
        else:
            return source_width, source_height
        if not spec.upscale:
            scale = min(scale, 1.0)
        return round(source_width * scale), round(source_height * scale)


class UnsplashPictureBackend(BasePictureBackend):
    alias = "unsplash"
    label = _("Unsplash")
    selection_field_name = "unsplash_image"
    configuration_fields = frozenset(
        {
            "use_automatic_scaling",
            "use_no_cropping",
            "use_crop",
            "use_upscale",
            "use_responsive_image",
        }
    )
    capabilities = UNSPLASH_CAPABILITIES

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)
        if not str(options.get("access_key", "")).strip():
            raise ImproperlyConfigured("The Unsplash backend requires an access_key option.")
        if not str(options.get("application_name", "")).strip():
            raise ImproperlyConfigured("The Unsplash backend requires an application_name option.")
        try:
            per_page = int(options.get("per_page", 20))
        except (TypeError, ValueError) as error:
            raise ImproperlyConfigured("Unsplash per_page must be an integer from 1 to 30.") from error
        if not 1 <= per_page <= 30:
            raise ImproperlyConfigured("Unsplash per_page must be an integer from 1 to 30.")
        content_filter = options.get("content_filter", "high")
        if content_filter not in {"low", "high"}:
            raise ImproperlyConfigured('Unsplash content_filter must be "low" or "high".')
        orientation = options.get("orientation", "")
        if orientation not in {"", "landscape", "portrait", "squarish"}:
            raise ImproperlyConfigured(
                'Unsplash orientation must be "landscape", "portrait", or "squarish".'
            )
        color = options.get("color", "")
        if color not in UNSPLASH_COLORS:
            raise ImproperlyConfigured("Unsplash color is not a supported search colour.")
        order_by = options.get("order_by", "relevant")
        if order_by not in {"relevant", "latest"}:
            raise ImproperlyConfigured('Unsplash order_by must be "relevant" or "latest".')
        collections = options.get("collections", ())
        if isinstance(collections, str):
            collections = tuple(value.strip() for value in collections.split(",") if value.strip())
        elif isinstance(collections, Sequence):
            collections = tuple(str(value).strip() for value in collections if str(value).strip())
        else:
            raise ImproperlyConfigured("Unsplash collections must be a string or sequence.")
        self.per_page = per_page
        self.collections = collections

    @property
    def application_name(self) -> str:
        return str(self.options["application_name"]).strip()

    @property
    def allowed_image_hosts(self) -> Sequence[str]:
        return self.options.get("allowed_image_hosts", ("images.unsplash.com",))

    def form_field(
        self,
        *,
        required: bool = True,
        request: Any = None,
        **kwargs: Any,
    ) -> UnsplashImageChoiceField:
        return UnsplashImageChoiceField(
            required=required,
            picker_url=self.get_picker_url(),
            application_name=self.application_name,
            allowed_image_hosts=self.allowed_image_hosts,
            **kwargs,
        )

    def get_picker_url(self) -> str:
        configured_url = self.options.get("picker_url")
        if configured_url:
            return _with_admin_popup_parameter(str(configured_url))
        try:
            picker_url = reverse("admin:djangocms_picture_unsplash_picker")
        except NoReverseMatch as error:
            raise ImproperlyConfigured(
                "The Unsplash picker admin URL is unavailable. Ensure django CMS admin "
                "URLs are included, or configure the Unsplash picker_url option."
            ) from error
        return _with_admin_popup_parameter(picker_url)

    def serialize(self, value: Any) -> PictureReference | None:
        if not value:
            return None
        snapshot = normalize_unsplash_payload(
            value,
            application_name=self.application_name,
            allowed_image_hosts=self.allowed_image_hosts,
        )
        return PictureReference(
            backend=self.alias,
            id=snapshot["id"],
            context={"application_name": self.application_name},
            snapshot=snapshot,
        )

    def resolve(self, reference: PictureReference) -> UnsplashImageAsset | None:
        if reference.backend != self.alias or not reference.snapshot:
            return None
        try:
            snapshot = normalize_unsplash_payload(
                reference.snapshot,
                application_name=self.application_name,
                allowed_image_hosts=self.allowed_image_hosts,
            )
        except ValueError:
            return None
        return UnsplashImageAsset(
            PictureReference(
                backend=self.alias,
                id=snapshot["id"],
                context=reference.context,
                snapshot=snapshot,
            )
        )

    def get_asset(self, picture_instance: Any) -> UnsplashImageAsset | None:
        reference = self.get_stored_reference(picture_instance)
        return self.resolve(reference) if reference else None

    def get_form_value(self, picture_instance: Any) -> dict[str, Any] | None:
        reference = self.get_stored_reference(picture_instance)
        return dict(reference.snapshot) if reference else None


def _replace_image_query(url: str, params: dict[str, str | int]) -> str:
    if not params:
        return url
    parsed = urlsplit(url)
    replaced_keys = set(params)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in replaced_keys
    ]
    query.extend((key, str(value)) for key, value in params.items())
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


def _output_params(transform: Any) -> dict[str, str | int]:
    if not isinstance(transform, Mapping):
        return {}
    params: dict[str, str | int] = {}
    if transform.get("format"):
        params["fm"] = str(transform["format"])
    if transform.get("quality") is not None:
        params["q"] = int(transform["quality"])
    return params


def _with_admin_popup_parameter(url: str) -> str:
    parsed = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key != IS_POPUP_VAR
    ]
    query.append((IS_POPUP_VAR, "1"))
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
    )
