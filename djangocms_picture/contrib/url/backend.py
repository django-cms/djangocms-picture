from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from djangocms_picture.backends.base import BaseImageAsset, BasePictureBackend
from djangocms_picture.backends.types import (
    BackendCapabilities,
    ImageAttribution,
    ImageInfo,
    PictureReference,
    Rendition,
    RenditionSpec,
)

URL_CAPABILITIES = BackendCapabilities(remote=True)


class URLImageAsset(BaseImageAsset):
    capabilities = URL_CAPABILITIES

    def __init__(self, reference: PictureReference) -> None:
        self.reference = reference
        snapshot = reference.snapshot
        self.info = ImageInfo(
            label=snapshot.get("label") or reference.id,
            width=snapshot.get("width"),
            height=snapshot.get("height"),
            alt_text=snapshot.get("alt_text", ""),
        )
        self.attribution = ImageAttribution.from_mapping(snapshot.get("attribution"))

    def get_original(self) -> Rendition:
        return Rendition(url=self.reference.id, width=self.info.width, height=self.info.height)

    def get_rendition(self, spec: RenditionSpec) -> Rendition:
        return self.get_original()


class URLPictureBackend(BasePictureBackend):
    alias = "url"
    label = _("External URL")
    selection_field_name = "external_picture"
    configuration_fields = frozenset()
    capabilities = URL_CAPABILITIES

    def form_field(self, *, required: bool = True, request: Any = None, **kwargs: Any) -> forms.URLField:
        return forms.URLField(required=required, **kwargs)

    def serialize(self, value: Any) -> PictureReference | None:
        if not value:
            return None
        return PictureReference(backend=self.alias, id=str(value))

    def resolve(self, reference: PictureReference) -> URLImageAsset | None:
        if reference.backend != self.alias or not reference.id:
            return None
        return URLImageAsset(reference)

    def get_asset(self, picture_instance: Any) -> URLImageAsset | None:
        reference = self.get_stored_reference(picture_instance)
        return self.resolve(reference) if reference else None
