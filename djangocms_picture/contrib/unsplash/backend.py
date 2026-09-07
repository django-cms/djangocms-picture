from collections.abc import Sequence
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.core.exceptions import ImproperlyConfigured
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

from .data import normalize_unsplash_payload
from .forms import UnsplashImageChoiceField
from .models import UnsplashPictureReference

UNSPLASH_FORMATS = ("jpg", "png", "webp")
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
        return Rendition(
            url=str(self.reference.snapshot["full_url"]),
            width=self.info.width,
            height=self.info.height,
        )

    def get_rendition(self, spec: RenditionSpec) -> Rendition:
        if spec.format and spec.format not in UNSPLASH_FORMATS:
            raise PictureBackendError(f'Unsplash does not support the "{spec.format}" format.')
        if spec.quality is not None and not 0 <= spec.quality <= 100:
            raise PictureBackendError("Unsplash rendition quality must be between 0 and 100.")

        width, height = self._rendition_dimensions(spec)
        params: dict[str, str | int] = {}
        if width:
            params["w"] = width
        if height:
            params["h"] = height
        if spec.crop and width and height:
            params.update({"fit": "crop", "crop": "entropy"})
        elif width or height:
            params["fit"] = "max"
        if spec.format:
            params["fm"] = spec.format
        if spec.quality is not None:
            params["q"] = spec.quality

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
        self.per_page = per_page

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
            access_key=str(self.options["access_key"]).strip(),
            application_name=self.application_name,
            per_page=self.per_page,
            content_filter=self.options.get("content_filter", "high"),
            orientation=self.options.get("orientation", ""),
            allowed_image_hosts=self.allowed_image_hosts,
            **kwargs,
        )

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
        if not getattr(picture_instance, "pk", None):
            return None
        try:
            extension = picture_instance.unsplash_reference
        except UnsplashPictureReference.DoesNotExist:
            return None
        return self.resolve(
            PictureReference(
                backend=self.alias,
                id=extension.asset_id,
                context={"application_name": self.application_name},
                snapshot=extension.snapshot,
            )
        )

    def get_form_value(self, picture_instance: Any) -> dict[str, Any] | None:
        if not getattr(picture_instance, "pk", None):
            return None
        try:
            return dict(picture_instance.unsplash_reference.snapshot)
        except UnsplashPictureReference.DoesNotExist:
            return None

    def set_form_value(self, picture_instance: Any, value: Any, *, commit: bool = False) -> None:
        picture_instance._unsplash_image = value
        if not commit:
            return
        reference = self.serialize(value)
        if reference is None:
            UnsplashPictureReference.objects.filter(picture_plugin=picture_instance).delete()
            return
        UnsplashPictureReference.objects.update_or_create(
            picture_plugin=picture_instance,
            defaults={
                "asset_id": reference.id,
                "snapshot": dict(reference.snapshot),
            },
        )

    def copy_reference(self, source: Any, target: Any) -> None:
        try:
            extension = source.unsplash_reference
        except UnsplashPictureReference.DoesNotExist:
            UnsplashPictureReference.objects.filter(picture_plugin=target).delete()
            return
        UnsplashPictureReference.objects.update_or_create(
            picture_plugin=target,
            defaults={
                "asset_id": extension.asset_id,
                "snapshot": extension.snapshot,
            },
        )


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
