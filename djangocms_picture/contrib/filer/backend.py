from typing import Any

from django.conf import settings
from easy_thumbnails.files import get_thumbnailer
from filer.utils.loader import load_model

from djangocms_picture.backends.base import BaseImageAsset, BasePictureBackend
from djangocms_picture.backends.types import BackendCapabilities, ImageInfo, PictureReference, Rendition, RenditionSpec

FILER_CAPABILITIES = BackendCapabilities(crop=True, upscale=True, responsive=True, presets=True, upload=True)


class FilerImageAsset(BaseImageAsset):
    capabilities = FILER_CAPABILITIES

    def __init__(self, image: Any) -> None:
        self.image = image
        self.reference = PictureReference(backend="filer", id=str(image.pk))
        self.info = ImageInfo(
            label=image.label or "",
            width=image.width,
            height=image.height,
            alt_text=getattr(image, "default_alt_text", "") or "",
        )

    def get_original(self) -> Rendition:
        return Rendition(url=self.image.url, width=self.image.width, height=self.image.height)

    def get_rendition(self, spec: RenditionSpec) -> Rendition:
        options = {
            "size": (spec.width, spec.height),
            "crop": spec.crop,
            "upscale": spec.upscale,
            "subject_location": self.image.subject_location,
        }
        thumbnail = get_thumbnailer(self.image).get_thumbnail(options)
        return Rendition(url=thumbnail.url, width=thumbnail.width, height=thumbnail.height)


class FilerPictureBackend(BasePictureBackend):
    alias = "filer"
    capabilities = FILER_CAPABILITIES

    def serialize(self, value: Any) -> PictureReference | None:
        if value is None:
            return None
        return PictureReference(backend=self.alias, id=str(value.pk))

    def resolve(self, reference: PictureReference) -> FilerImageAsset | None:
        if reference.backend != self.alias:
            return None
        image_model = load_model(settings.FILER_IMAGE_MODEL)
        try:
            image = image_model.objects.get(pk=reference.id)
        except (image_model.DoesNotExist, ValueError, TypeError):
            return None
        return FilerImageAsset(image)

    def get_asset(self, picture_instance: Any) -> FilerImageAsset | None:
        image = getattr(picture_instance, "picture", None)
        return FilerImageAsset(image) if image else None
