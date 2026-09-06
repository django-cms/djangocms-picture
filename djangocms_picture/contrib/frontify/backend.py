from collections.abc import Sequence
from typing import Any
from urllib.parse import urlencode

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from djangocms_picture.backends.base import (
    BaseImageAsset,
    BasePictureBackend,
    PictureBackendError,
)
from djangocms_picture.backends.types import (
    BackendCapabilities,
    ImageInfo,
    PictureReference,
    Rendition,
    RenditionSpec,
)

from .data import normalize_frontify_payload
from .forms import FrontifyImageChoiceField
from .models import FrontifyPictureReference

FRONTIFY_FORMATS = ("jpg", "jpeg", "png", "webp")
FRONTIFY_CAPABILITIES = BackendCapabilities(
    resize=True,
    crop=True,
    responsive=True,
    remote=True,
    permanent_urls=True,
    formats=FRONTIFY_FORMATS,
)
DEFAULT_FINDER_SCRIPT_URL = "https://unpkg.com/@frontify/frontify-finder@2.0.1/dist/index.js"


class FrontifyImageAsset(BaseImageAsset):
    capabilities = FRONTIFY_CAPABILITIES

    def __init__(self, reference: PictureReference) -> None:
        self.reference = reference
        snapshot = reference.snapshot
        self.info = ImageInfo(
            label=str(snapshot.get("label") or reference.id),
            width=snapshot.get("width"),
            height=snapshot.get("height"),
            alt_text=str(snapshot.get("alt_text") or ""),
        )

    def get_original(self) -> Rendition:
        snapshot = self.reference.snapshot
        return Rendition(
            url=str(snapshot["original_url"]),
            width=self.info.width,
            height=self.info.height,
        )

    def get_rendition(self, spec: RenditionSpec) -> Rendition:
        if spec.upscale:
            raise PictureBackendError("The Frontify backend does not support explicit upscaling.")
        if spec.format and spec.format not in FRONTIFY_FORMATS:
            raise PictureBackendError(f'Frontify does not support the "{spec.format}" format.')
        if spec.quality is not None and not 0 <= spec.quality <= 100:
            raise PictureBackendError("Frontify rendition quality must be between 0 and 100.")

        snapshot = self.reference.snapshot
        params: list[tuple[str, str | int]] = []
        if spec.width:
            params.append(("width", spec.width))
        if spec.height:
            params.append(("height", spec.height))
        if spec.format:
            params.append(("format", spec.format))
        if spec.quality is not None:
            params.append(("quality", spec.quality))
        if spec.crop:
            focal_point = snapshot.get("focal_point") or (0.5, 0.5)
            params.extend(
                (
                    ("crop", "fp"),
                    ("fp", f"{focal_point[0]},{focal_point[1]}"),
                )
            )

        width, height = self._rendition_dimensions(spec)
        processing_url = str(snapshot["processing_url"])
        url = f"{processing_url}?{urlencode(params)}" if params else processing_url
        return Rendition(url=url, width=width, height=height)

    def _rendition_dimensions(self, spec: RenditionSpec) -> tuple[int | None, int | None]:
        if spec.crop and spec.width and spec.height:
            return spec.width, spec.height
        source_width, source_height = self.info.width, self.info.height
        if not source_width or not source_height:
            return spec.width, spec.height
        if spec.width and spec.height:
            scale = min(spec.width / source_width, spec.height / source_height)
            return round(source_width * scale), round(source_height * scale)
        if spec.width:
            return spec.width, round(spec.width * source_height / source_width)
        if spec.height:
            return round(spec.height * source_width / source_height), spec.height
        return source_width, source_height


class FrontifyPictureBackend(BasePictureBackend):
    alias = "frontify"
    label = _("Frontify")
    selection_field_name = "frontify_image"
    configuration_fields = frozenset(
        {
            "use_automatic_scaling",
            "use_no_cropping",
            "use_crop",
            "use_responsive_image",
        }
    )
    capabilities = FRONTIFY_CAPABILITIES

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)
        if not options.get("allowed_hosts"):
            raise ImproperlyConfigured(
                "The Frontify backend requires a non-empty allowed_hosts option."
            )

    @property
    def allowed_hosts(self) -> Sequence[str]:
        return self.options.get("allowed_hosts", ())

    def form_field(
        self,
        *,
        required: bool = True,
        request: Any = None,
        **kwargs: Any,
    ) -> FrontifyImageChoiceField:
        return FrontifyImageChoiceField(
            required=required,
            domain=self.options.get("domain", ""),
            client_id=self.options.get("client_id", ""),
            finder_script_url=self.options.get(
                "finder_script_url",
                DEFAULT_FINDER_SCRIPT_URL,
            ),
            allowed_hosts=self.allowed_hosts,
            alt_text_field=self.options.get(
                "alt_text_field",
                "alt-tag_{language_code}",
            ),
            **kwargs,
        )

    def serialize(self, value: Any) -> PictureReference | None:
        if not value:
            return None
        snapshot = normalize_frontify_payload(
            value,
            allowed_hosts=self.allowed_hosts,
            alt_text_field=self.options.get(
                "alt_text_field",
                "alt-tag_{language_code}",
            ),
        )
        return PictureReference(
            backend=self.alias,
            id=snapshot["id"],
            context={"account": self.options.get("account", "")},
            snapshot=snapshot,
        )

    def resolve(self, reference: PictureReference) -> FrontifyImageAsset | None:
        if reference.backend != self.alias or not reference.snapshot:
            return None
        if reference.snapshot.get("disabled"):
            return None
        try:
            snapshot = normalize_frontify_payload(
                reference.snapshot,
                allowed_hosts=self.allowed_hosts,
                alt_text_field=self.options.get(
                    "alt_text_field",
                    "alt-tag_{language_code}",
                ),
            )
        except ValueError:
            return None
        return FrontifyImageAsset(
            PictureReference(
                backend=self.alias,
                id=snapshot["id"],
                context=reference.context,
                snapshot=snapshot,
            )
        )

    def get_asset(self, picture_instance: Any) -> FrontifyImageAsset | None:
        if not getattr(picture_instance, "pk", None):
            return None
        try:
            extension = picture_instance.frontify_reference
        except FrontifyPictureReference.DoesNotExist:
            return None
        if extension.disabled:
            return None
        reference = PictureReference(
            backend=self.alias,
            id=extension.asset_id,
            context={"account": extension.account},
            snapshot=extension.snapshot,
        )
        return self.resolve(reference)

    def get_form_value(self, picture_instance: Any) -> dict[str, Any] | None:
        asset = self.get_asset(picture_instance)
        return dict(asset.reference.snapshot) if asset else None

    def set_form_value(self, picture_instance: Any, value: Any, *, commit: bool = False) -> None:
        picture_instance._frontify_image = value
        if not commit:
            return
        reference = self.serialize(value)
        if reference is None:
            FrontifyPictureReference.objects.filter(picture_plugin=picture_instance).delete()
            return
        FrontifyPictureReference.objects.update_or_create(
            picture_plugin=picture_instance,
            defaults={
                "asset_id": reference.id,
                "account": str(reference.context.get("account", "")),
                "snapshot": dict(reference.snapshot),
                "revision": str(reference.snapshot.get("revision", "")),
                "disabled": False,
            },
        )

    def copy_reference(self, source: Any, target: Any) -> None:
        self.set_form_value(target, self.get_form_value(source), commit=True)
