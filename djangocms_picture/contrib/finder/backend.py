from pathlib import Path
from typing import Any

from django.core.files.images import get_image_dimensions
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from finder.models.file import AbstractFileModel, FileModel

from djangocms_picture.backends.base import BaseImageAsset, BasePictureBackend, PictureBackendError
from djangocms_picture.backends.types import BackendCapabilities, ImageInfo, PictureReference, Rendition, RenditionSpec

from .forms import FinderImageChoiceField
from .models import FinderPictureReference

FINDER_CAPABILITIES = BackendCapabilities(
    crop=True,
    responsive=False,
    # The finder picker can upload interactively, but backend.upload() does
    # not yet have enough folder/permission context for programmatic uploads.
    upload=False,
    formats=(),
)


class FinderImageAsset(BaseImageAsset):
    capabilities = FINDER_CAPABILITIES

    def __init__(self, image: AbstractFileModel) -> None:
        self.image = image
        self.ambit = image.folder.get_ambit()
        self.reference = PictureReference(
            backend="finder",
            id=str(image.pk),
            context={"ambit": self.ambit.slug},
            snapshot={
                "label": image.name,
                "width": image.width,
                "height": image.height,
                "alt_text": image.meta_data.get("alt_text", image.name),
                "mime_type": image.mime_type,
                "revision": image.sha1,
            },
        )
        self.info = ImageInfo(
            label=image.name,
            width=image.width or None,
            height=image.height or None,
            alt_text=image.meta_data.get("alt_text", image.name),
        )

    def get_original(self) -> Rendition:
        return Rendition(
            url=self.image.get_download_url(self.ambit),
            width=self.info.width,
            height=self.info.height,
        )

    def get_rendition(self, spec: RenditionSpec) -> Rendition:
        if not spec.crop or not spec.width or not spec.height:
            return self.get_original()
        if not hasattr(self.image, "crop"):
            raise PictureBackendError(f'Finder image type "{self.image.mime_type}" cannot generate crops.')

        filename = self.image.get_cropped_filename(spec.width, spec.height)
        rendition_path = f"{self.image.id}/{filename}"
        try:
            if not self.ambit.sample_storage.exists(rendition_path):
                self.image.crop(self.ambit, rendition_path, spec.width, spec.height)
            width, height = self._get_dimensions(rendition_path)
            url = self.ambit.sample_storage.url(rendition_path)
        except Exception as error:
            raise PictureBackendError(f"Finder could not generate rendition {rendition_path}.") from error
        return Rendition(url=url, width=width, height=height)

    def _get_dimensions(self, rendition_path: str) -> tuple[int | None, int | None]:
        with self.ambit.sample_storage.open(rendition_path, "rb") as image_file:
            if Path(rendition_path).suffix.lower() == ".svg":
                from finder.utils.svg import get_dimensions

                width, height = get_dimensions(image_file)
                return round(width), round(height)
            return get_image_dimensions(image_file)


class FinderPictureBackend(BasePictureBackend):
    alias = "finder"
    label = _("Finder")
    selection_field_name = "finder_image"
    configuration_fields = frozenset(
        {
            "use_automatic_scaling",
            "use_no_cropping",
            "use_crop",
        }
    )
    capabilities = FINDER_CAPABILITIES

    @property
    def ambit(self) -> str | None:
        return self.options.get("ambit")

    def form_field(self, *, required: bool = True, request: Any = None, **kwargs: Any) -> FinderImageChoiceField:
        if self.ambit:
            kwargs.setdefault("ambit", self.ambit)
        return FinderImageChoiceField(
            required=required,
            accept_mime_types=["image/*"],
            **kwargs,
        )

    def serialize(self, value: Any) -> PictureReference | None:
        if not value:
            return None
        image = value if isinstance(value, AbstractFileModel) else self._resolve_id(value)
        return FinderImageAsset(image).reference if image else None

    def resolve(self, reference: PictureReference) -> FinderImageAsset | None:
        if reference.backend != self.alias:
            return None
        image = self._resolve_id(reference.id)
        return FinderImageAsset(image) if image else None

    def get_asset(self, picture_instance: Any) -> FinderImageAsset | None:
        if not getattr(picture_instance, "pk", None):
            return None
        try:
            extension = picture_instance.finder_reference
        except FinderPictureReference.DoesNotExist:
            return None
        if not extension.image:
            return None
        image = extension.image
        if not isinstance(image, AbstractFileModel):
            image = self._resolve_id(image)
        return FinderImageAsset(image) if image else None

    def set_form_value(self, picture_instance: Any, value: Any, *, commit: bool = False) -> None:
        picture_instance._finder_image = value
        if not commit:
            return

        reference = self.serialize(value)
        snapshot = dict(reference.snapshot) if reference else {}
        ambit = str(reference.context.get("ambit", "")) if reference else ""
        with transaction.atomic():
            FinderPictureReference.objects.update_or_create(
                picture_plugin=picture_instance,
                defaults={"image": value, "ambit": ambit, "snapshot": snapshot},
            )

    @staticmethod
    def _resolve_id(image_id: Any) -> AbstractFileModel | None:
        try:
            return FileModel.objects.get_inode(id=image_id, is_folder=False, mime_types=["image/*"])
        except (FileModel.DoesNotExist, TypeError, ValueError):
            return None
