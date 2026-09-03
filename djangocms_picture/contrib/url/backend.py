from typing import Any

from django import forms

from djangocms_picture.backends.base import BaseImageAsset, BasePictureBackend
from djangocms_picture.backends.types import BackendCapabilities, ImageInfo, PictureReference, Rendition, RenditionSpec

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

    def get_original(self) -> Rendition:
        return Rendition(url=self.reference.id, width=self.info.width, height=self.info.height)

    def get_rendition(self, spec: RenditionSpec) -> Rendition:
        return self.get_original()


class URLPictureBackend(BasePictureBackend):
    alias = "url"
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
        url = getattr(picture_instance, "external_picture", None)
        if not url:
            return None
        # Historically get_size() continued to use a retained filer image's
        # dimensions while external_picture overrode its URL. Preserve that
        # behavior until render data is an explicitly versioned public API.
        legacy_image = getattr(picture_instance, "picture", None)
        reference = PictureReference(
            backend=self.alias,
            id=url,
            snapshot={
                "width": getattr(legacy_image, "width", None),
                "height": getattr(legacy_image, "height", None),
            },
        )
        return URLImageAsset(reference)
