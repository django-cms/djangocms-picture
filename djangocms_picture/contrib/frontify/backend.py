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
    ImageAttribution,
    ImageInfo,
    PictureReference,
    Rendition,
    RenditionSpec,
)

from .data import is_frontify_snapshot_expired, normalize_frontify_payload
from .forms import FrontifyImageChoiceField

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
        self.attribution = ImageAttribution.from_mapping(snapshot.get("attribution"))

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
        reference = self.get_stored_reference(picture_instance)
        return self.resolve(reference) if reference else None

    def get_form_value(self, picture_instance: Any) -> dict[str, Any] | None:
        reference = self.get_stored_reference(picture_instance)
        if reference is None or reference.snapshot.get("disabled"):
            return None
        return dict(reference.snapshot)

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
        reference = self.get_stored_reference(picture_instance)
        if reference is None:
            raise PictureBackendError("The picture has no Frontify reference to refresh.")
        try:
            refreshed = self.refresh(reference, request=request)
        except FrontifyAssetRevoked:
            if commit:
                snapshot = {
                    **reference.snapshot,
                    "disabled": True,
                    "refreshed_at": timezone.now().isoformat(),
                }
                picture_instance.picture_config = replace(reference, snapshot=snapshot).as_dict()
                picture_instance.save(update_fields=("picture_config",))
            return None
        if commit:
            snapshot = {
                **refreshed.snapshot,
                "disabled": False,
                "refreshed_at": timezone.now().isoformat(),
            }
            picture_instance.picture_config = replace(refreshed, snapshot=snapshot).as_dict()
            picture_instance.save(update_fields=("picture_config",))
        return refreshed

    def revoke(self, asset_id: str) -> int:
        """Disable stored references from an authenticated application webhook."""

        from djangocms_picture.models import Picture

        count = 0
        for picture in Picture.objects.filter(
            backend=self.alias,
            picture_config__id=asset_id,
        ).iterator():
            reference = self.get_stored_reference(picture)
            if reference is None:
                continue
            snapshot = {
                **reference.snapshot,
                "disabled": True,
                "refreshed_at": timezone.now().isoformat(),
            }
            Picture.objects.filter(pk=picture.pk).update(
                picture_config=replace(reference, snapshot=snapshot).as_dict()
            )
            count += 1
        return count


def _append_query(url: str, params: list[tuple[str, str | int]]) -> str:
    if not params:
        return url
    parsed = urlsplit(url)
    query = [*parse_qsl(parsed.query, keep_blank_values=True), *params]
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))
