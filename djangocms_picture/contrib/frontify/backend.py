from collections.abc import Sequence
from dataclasses import replace
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.utils.module_loading import import_string
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

from .data import is_frontify_snapshot_expired, normalize_frontify_payload
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
DEFAULT_FINDER_SCRIPT_URL = "djangocms_picture/vendor/frontify-finder/index.js"


class FrontifyAssetRevoked(PictureBackendError):
    """Raised by a refresher when Frontify no longer exposes an asset."""


class FrontifyImageAsset(BaseImageAsset):
    capabilities = FRONTIFY_CAPABILITIES

    def __init__(
        self,
        reference: PictureReference,
        *,
        capabilities: BackendCapabilities = FRONTIFY_CAPABILITIES,
    ) -> None:
        self.reference = reference
        self.capabilities = capabilities
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
        url = _append_query(processing_url, params)
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
        refresher = options.get("refresher")
        if isinstance(refresher, str):
            refresher = import_string(refresher)
        if refresher is not None and not callable(refresher):
            raise ImproperlyConfigured("The Frontify refresher option must be callable or an import path.")
        self._refresher = refresher
        self.capabilities = replace(
            FRONTIFY_CAPABILITIES,
            refresh=refresher is not None,
            permanent_urls=not bool(options.get("allow_expiring_urls", False)),
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
            allow_expiring_urls=bool(self.options.get("allow_expiring_urls", False)),
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
        if snapshot.get("expires_at") and not self.options.get("allow_expiring_urls", False):
            raise PictureBackendError(
                "Frontify returned expiring URLs; enable allow_expiring_urls or request permanent download URLs."
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
            if is_frontify_snapshot_expired(
                reference.snapshot,
                leeway_seconds=int(self.options.get("expiry_leeway_seconds", 0)),
            ):
                return None
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
            ),
            capabilities=self.capabilities,
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
        if not getattr(picture_instance, "pk", None):
            return None
        try:
            extension = picture_instance.frontify_reference
        except FrontifyPictureReference.DoesNotExist:
            return None
        return dict(extension.snapshot) if not extension.disabled else None

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
                "refreshed_at": timezone.now(),
                "disabled": False,
            },
        )

    def copy_reference(self, source: Any, target: Any) -> None:
        try:
            extension = source.frontify_reference
        except FrontifyPictureReference.DoesNotExist:
            FrontifyPictureReference.objects.filter(picture_plugin=target).delete()
            return
        FrontifyPictureReference.objects.update_or_create(
            picture_plugin=target,
            defaults={
                "asset_id": extension.asset_id,
                "account": extension.account,
                "snapshot": extension.snapshot,
                "revision": extension.revision,
                "refreshed_at": extension.refreshed_at,
                "disabled": extension.disabled,
            },
        )

    def refresh(self, reference: PictureReference, *, request: Any = None) -> PictureReference:
        if reference.backend != self.alias:
            raise PictureBackendError("A Frontify backend can only refresh Frontify references.")
        if self._refresher is None:
            return super().refresh(reference, request=request)
        payload = self._refresher(reference, request=request)
        if payload is None:
            raise FrontifyAssetRevoked(f'Frontify asset "{reference.id}" is no longer available.')
        refreshed = self.serialize(payload)
        if refreshed is None or refreshed.id != reference.id:
            raise PictureBackendError("A Frontify refresh must return the same asset id.")
        return PictureReference(
            backend=self.alias,
            id=refreshed.id,
            context=reference.context,
            snapshot=refreshed.snapshot,
        )

    def refresh_instance(
        self,
        picture_instance: Any,
        *,
        request: Any = None,
        commit: bool = True,
    ) -> PictureReference | None:
        try:
            extension = picture_instance.frontify_reference
        except FrontifyPictureReference.DoesNotExist as error:
            raise PictureBackendError("The picture has no Frontify reference to refresh.") from error
        reference = PictureReference(
            backend=self.alias,
            id=extension.asset_id,
            context={"account": extension.account},
            snapshot=extension.snapshot,
        )
        try:
            refreshed = self.refresh(reference, request=request)
        except FrontifyAssetRevoked:
            if commit:
                extension.disabled = True
                extension.refreshed_at = timezone.now()
                extension.save(update_fields=("disabled", "refreshed_at"))
            return None
        if commit:
            extension.snapshot = dict(refreshed.snapshot)
            extension.revision = str(refreshed.snapshot.get("revision", ""))
            extension.refreshed_at = timezone.now()
            extension.disabled = False
            extension.save(update_fields=("snapshot", "revision", "refreshed_at", "disabled"))
        return refreshed

    def revoke(self, asset_id: str) -> int:
        """Disable stored references from an authenticated application webhook."""

        return FrontifyPictureReference.objects.filter(asset_id=asset_id).update(
            disabled=True,
            refreshed_at=timezone.now(),
        )


def _append_query(url: str, params: list[tuple[str, str | int]]) -> str:
    if not params:
        return url
    parsed = urlsplit(url)
    query = [*parse_qsl(parsed.query, keep_blank_values=True), *params]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))
