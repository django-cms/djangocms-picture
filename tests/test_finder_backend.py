from pathlib import Path

import pytest
from django.apps import apps

pytest.importorskip("finder")
if not apps.is_installed("djangocms_picture.contrib.finder"):
    pytest.skip("The finder contrib app is not installed.", allow_module_level=True)

from django.core.files import File
from django.forms import modelform_factory
from django.test import TestCase
from finder.contrib.image.models import ImageFileModel
from finder.models.ambit import AmbitModel
from finder.models.folder import FolderModel

from djangocms_picture.backends import PictureReference, RenditionSpec, get_backend
from djangocms_picture.contrib.finder.backend import FinderPictureBackend
from djangocms_picture.forms import PictureForm
from djangocms_picture.models import Picture

from .helpers import get_image


class FinderBackendTestCase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.root = FolderModel.objects.create(name="Root")
        cls.ambit = AmbitModel.objects.create(
            slug="public",
            verbose_name="Public",
            site=None,
            root_folder=cls.root,
            _original_storage="finder_public",
            _sample_storage="finder_public_samples",
        )
        payload = get_image(size=(800, 600))
        cls.image = ImageFileModel.objects.create(
            parent=cls.root,
            name="finder-image.jpg",
            file_name="finder-image.jpg",
            file_size=Path(payload["path"]).stat().st_size,
            mime_type="image/jpeg",
            width=800,
            height=600,
            sha1="draft-revision",
        )
        with Path(payload["path"]).open("rb") as image_file:
            cls.ambit.original_storage.save(cls.image.file_path, File(image_file))

    def test_backend_declares_current_finder_capabilities(self) -> None:
        backend = get_backend("finder")

        self.assertIsInstance(backend, FinderPictureBackend)
        self.assertTrue(backend.capabilities.crop)
        self.assertFalse(backend.capabilities.resize)
        self.assertFalse(backend.capabilities.upscale)
        self.assertFalse(backend.capabilities.responsive)
        self.assertFalse(backend.capabilities.upload)

    def test_form_uses_finder_picker_and_disables_unsupported_options(self) -> None:
        form = PictureForm()

        self.assertEqual(form.initial["backend"], "finder")
        self.assertIn("finder_image", form.fields)
        self.assertFalse(form.fields["finder_image"].disabled)
        self.assertFalse(form.fields["use_crop"].disabled)
        self.assertTrue(form.fields["use_upscale"].disabled)
        self.assertTrue(form.fields["use_responsive_image"].disabled)
        self.assertTrue(form.fields["thumbnail_options"].disabled)
        self.assertIn("finder/js/finder-select.js", str(form.media))

    def test_finder_picker_survives_admin_form_subclassing(self) -> None:
        admin_form = modelform_factory(
            Picture,
            form=PictureForm,
            fields=("template", "backend", "finder_image"),
        )

        self.assertIn("finder_image", admin_form.base_fields)

    def test_form_persists_finder_selection(self) -> None:
        form = PictureForm(
            data={
                "backend": "finder",
                "finder_image": str(self.image.id),
                "template": "default",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        picture = form.save()
        picture.refresh_from_db()
        self.assertEqual(picture.backend, "finder")
        self.assertEqual(picture.picture_reference.id, str(self.image.id))

    def test_admin_deferred_save_persists_finder_selection(self) -> None:
        form = PictureForm(
            data={
                "backend": "finder",
                "finder_image": str(self.image.id),
                "template": "default",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        picture = form.save(commit=False)
        picture.save()
        form.save_m2m()
        picture.refresh_from_db()

        self.assertEqual(picture.picture_reference.id, str(self.image.id))

    def test_existing_finder_selection_initializes_picker(self) -> None:
        picture = Picture.objects.create(backend="finder")
        get_backend("finder").set_form_value(picture, self.image.id, commit=True)

        form = PictureForm(instance=picture)

        self.assertEqual(form["finder_image"].value(), str(self.image.id))

    def test_reference_is_persisted_in_typed_extension(self) -> None:
        picture = Picture.objects.create(backend="finder")
        backend = get_backend("finder")

        backend.set_form_value(picture, self.image.id, commit=True)
        picture.refresh_from_db()

        self.assertEqual(picture.finder_reference.image.id, self.image.id)
        self.assertEqual(picture.finder_reference.ambit, "public")
        self.assertEqual(picture.picture_reference.backend, "finder")
        self.assertEqual(picture.picture_reference.id, str(self.image.id))

    def test_focal_crop_is_generated_in_sample_storage(self) -> None:
        asset = get_backend("finder").resolve(
            PictureReference(backend="finder", id=str(self.image.id))
        )
        self.assertIsNotNone(asset)

        rendition = asset.get_rendition(RenditionSpec(width=200, height=200, crop=True))

        self.assertEqual((rendition.width, rendition.height), (200, 200))
        self.assertTrue(rendition.url.startswith("/media/finder-samples/"))

    def test_uncropped_rendition_uses_original(self) -> None:
        asset = get_backend("finder").resolve(
            PictureReference(backend="finder", id=str(self.image.id))
        )
        self.assertIsNotNone(asset)

        rendition = asset.get_rendition(RenditionSpec(width=200, height=150))

        self.assertEqual((rendition.width, rendition.height), (800, 600))
        self.assertTrue(rendition.url.startswith("/media/finder/"))
