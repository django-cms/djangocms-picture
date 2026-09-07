from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from django.apps import apps

pytest.importorskip("finder")
if not apps.is_installed("djangocms_picture.contrib.finder"):
    pytest.skip("The finder contrib app is not installed.", allow_module_level=True)

from cms.api import add_plugin
from cms.models import Placeholder
from cms.utils.plugins import copy_plugins_to_placeholder
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.forms import modelform_factory
from django.test import TestCase
from finder.contrib.image.models import ImageFileModel
from finder.models.ambit import AmbitModel
from finder.models.folder import FolderModel

from djangocms_picture.backends import PictureBackendError, PictureReference, RenditionSpec, get_backend
from djangocms_picture.contrib.finder.backend import FinderImageAsset, FinderPictureBackend
from djangocms_picture.contrib.finder.forms import FinderImageChoiceField
from djangocms_picture.fields import BackendSelection
from djangocms_picture.forms import PictureForm
from djangocms_picture.models import Picture

from .helpers import get_filer_image, get_image


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
        cls.trash = FolderModel.objects.create(name="__trash__")
        cls.ambit.trash_folders.add(cls.trash)
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

        cls.private_root = FolderModel.objects.create(name="Private root")
        cls.private_ambit = AmbitModel.objects.create(
            slug="private",
            verbose_name="Private",
            site=None,
            root_folder=cls.private_root,
            _original_storage="finder_private",
            _sample_storage="finder_private_samples",
        )
        cls.private_image = ImageFileModel.objects.create(
            parent=cls.private_root,
            name="private.jpg",
            file_name="private.jpg",
            file_size=100,
            mime_type="image/jpeg",
            width=100,
            height=100,
            sha1="private-revision",
        )

    def test_backend_declares_current_finder_capabilities(self) -> None:
        backend = get_backend("finder")

        self.assertIsInstance(backend, FinderPictureBackend)
        self.assertTrue(backend.capabilities.crop)
        self.assertFalse(backend.capabilities.resize)
        self.assertFalse(backend.capabilities.upscale)
        self.assertFalse(backend.capabilities.responsive)
        self.assertFalse(backend.capabilities.upload)

    def test_backend_uses_finder_default_ambit_when_unconfigured(self) -> None:
        field = FinderPictureBackend().form_field(required=False)

        self.assertEqual(field.ambit, "public")

    def test_form_uses_finder_picker_and_disables_unsupported_options(self) -> None:
        form = PictureForm()
        source_field = form.fields["image_source"]

        self.assertEqual(
            form.initial["image_source"],
            BackendSelection(get_backend("finder"), None),
        )
        self.assertIsInstance(source_field.backend_fields["finder"], FinderImageChoiceField)
        self.assertFalse(form.fields["use_crop"].disabled)
        self.assertTrue(form.fields["use_upscale"].disabled)
        self.assertTrue(form.fields["use_responsive_image"].disabled)
        self.assertTrue(form.fields["thumbnail_options"].disabled)
        self.assertIn("finder/js/finder-select.js", str(form.media))

        html = source_field.widget.render(
            "image_source",
            form.initial["image_source"],
            attrs={"id": "id_image_source"},
        )
        self.assertIn("<finder-file-select", html)
        self.assertIn('name="image_source_finder"', html)

    def test_finder_picker_survives_admin_form_subclassing(self) -> None:
        admin_form = modelform_factory(
            Picture,
            form=PictureForm,
            fields=("template", "image_source"),
        )

        self.assertIn("image_source", admin_form.base_fields)

    def test_form_persists_finder_selection(self) -> None:
        form = PictureForm(
            data={
                "image_source_backend": "finder",
                "image_source_finder": str(self.image.id),
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
                "image_source_backend": "finder",
                "image_source_finder": str(self.image.id),
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

        self.assertEqual(
            form.initial["image_source"],
            BackendSelection(get_backend("finder"), str(self.image.id)),
        )
        self.assertEqual(picture.image_alt_text, self.image.name)

    def test_asset_exposes_generic_attribution_metadata(self) -> None:
        self.image.meta_data = {
            "author": "Example Photographer",
            "author_url": "https://example.com/photographer",
            "copyright": "© Example Photographer",
            "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
        }

        attribution = FinderImageAsset(self.image).attribution

        self.assertIsNotNone(attribution)
        self.assertEqual(attribution.creator_name, "Example Photographer")
        self.assertEqual(attribution.copyright_notice, "© Example Photographer")
        self.assertEqual(attribution.license_name, "CC BY 4.0")

    def test_reference_is_persisted_in_typed_extension(self) -> None:
        picture = Picture.objects.create(backend="finder")
        backend = get_backend("finder")

        backend.set_form_value(picture, self.image.id, commit=True)
        picture.refresh_from_db()

        self.assertEqual(picture.finder_reference.image.id, self.image.id)
        self.assertEqual(picture.finder_reference.ambit, "public")
        self.assertEqual(picture.picture_reference.backend, "finder")
        self.assertEqual(picture.picture_reference.id, str(self.image.id))

    def test_plugin_copy_and_clear_use_finder_lifecycle_hooks(self) -> None:
        source = Picture.objects.create(backend="finder")
        target = Picture.objects.create(backend="finder")
        backend = get_backend("finder")
        backend.set_form_value(source, self.image.id, commit=True)

        target.copy_relations(source)
        target.refresh_from_db()
        self.assertEqual(target.finder_reference.image.id, self.image.id)
        self.assertEqual(target.backend, "finder")

        backend.clear_reference(target, commit=True)
        self.assertFalse(
            target.__class__.objects.filter(
                finder_reference__picture_plugin=target
            ).exists()
        )

    def test_backend_handles_empty_stale_and_foreign_references(self) -> None:
        backend = get_backend("finder")
        unsaved_picture = Picture(backend="finder")
        picture_without_reference = Picture.objects.create(backend="finder")

        self.assertIsNone(backend.serialize(None))
        self.assertIsNone(backend.serialize(uuid4()))
        self.assertIsNone(backend.resolve(PictureReference(backend="url", id=str(self.image.id))))
        self.assertIsNone(backend.resolve(PictureReference(backend="finder", id=str(uuid4()))))
        self.assertIsNone(backend.get_asset(unsaved_picture))
        self.assertIsNone(backend.get_asset(picture_without_reference))

        backend.set_form_value(picture_without_reference, None, commit=True)
        self.assertIsNone(backend.get_asset(picture_without_reference))

    def test_backend_serializes_a_finder_image_instance(self) -> None:
        reference = get_backend("finder").serialize(self.image)

        self.assertIsNotNone(reference)
        self.assertEqual(reference.id, str(self.image.id))

    def test_backend_selection_serialization_restores_uuid_value(self) -> None:
        selection = BackendSelection(get_backend("finder"), self.image.id)

        serialized = selection.serialize()
        restored = BackendSelection.deserialize(serialized)

        self.assertEqual(
            serialized,
            {"version": 1, "backend": "finder", "value": str(self.image.id)},
        )
        self.assertEqual(restored, selection)

    def test_picker_rejects_missing_and_non_image_inodes(self) -> None:
        field = FinderImageChoiceField(
            required=False,
            ambit="public",
            allowed_ambits=("public",),
        )

        self.assertIsNone(field.clean(""))
        with self.assertRaises(ValidationError):
            field.clean(uuid4())
        with self.assertRaises(ValidationError):
            field.clean(self.root.id)

    def test_private_ambit_is_rejected_by_picker_and_resolver(self) -> None:
        backend = get_backend("finder")

        with self.assertRaisesMessage(ValidationError, "not available"):
            backend.form_field().clean(self.private_image.id)
        self.assertIsNone(
            backend.resolve(
                PictureReference(backend="finder", id=str(self.private_image.id))
            )
        )

    def test_trashed_image_keeps_rendering_but_cannot_be_selected_again(self) -> None:
        image = ImageFileModel.objects.get(pk=self.image.pk)
        image.parent = self.trash
        image.save(update_fields=("parent",))
        backend = get_backend("finder")

        with self.assertRaisesMessage(ValidationError, "in the trash"):
            backend.form_field().clean(image.id)
        self.assertIsNotNone(
            backend.resolve(PictureReference(backend="finder", id=str(image.id)))
        )

    def test_hard_deleted_finder_image_leaves_a_non_rendering_tombstone(self) -> None:
        image = ImageFileModel.objects.get(pk=self.image.pk)
        picture = Picture.objects.create(backend="finder")
        get_backend("finder").set_form_value(picture, image.id, commit=True)

        image.delete()
        picture.refresh_from_db()

        self.assertIsNone(picture.finder_reference.image)
        self.assertIsNone(picture.image_asset)

    def test_real_cms_plugin_copy_preserves_finder_reference(self) -> None:
        source_placeholder = Placeholder.objects.create(slot="source")
        target_placeholder = Placeholder.objects.create(slot="target")
        source = add_plugin(
            source_placeholder,
            "PicturePlugin",
            "en",
            backend="finder",
            template="default",
        )
        get_backend("finder").set_form_value(source, self.image.id, commit=True)

        copies = copy_plugins_to_placeholder(
            [source],
            target_placeholder,
            language="en",
            plugins_are_downcast=True,
        )

        copied = copies[0]
        copied.refresh_from_db()
        self.assertEqual(copied.backend, "finder")
        self.assertEqual(copied.finder_reference.image.id, self.image.id)

    def test_filer_migration_is_dry_runnable_auditable_and_reversible(self) -> None:
        filer_image = get_filer_image("migration.jpg")
        finder_id = UUID(Path(filer_image.file.name).parent.name)
        migrated_image = ImageFileModel.objects.create(
            id=finder_id,
            parent=self.root,
            name="migration.jpg",
            file_name="migration.jpg",
            file_size=filer_image._file_size,
            mime_type="image/jpeg",
            width=filer_image.width,
            height=filer_image.height,
            sha1=filer_image.sha1,
        )
        picture = Picture.objects.create(
            backend="filer",
            picture=filer_image,
            template="default",
        )
        output = StringIO()

        with TemporaryDirectory() as audit_directory:
            audit_file = Path(audit_directory) / "pictures.jsonl"
            call_command(
                "migrate_picture_backend",
                source="filer",
                destination="finder",
                ambit="public",
                dry_run=True,
                batch_size=1,
                after_pk=picture.pk - 1,
                limit=1,
                audit_file=audit_file,
                stdout=output,
            )
            self.assertIn('"status": "would_migrate"', audit_file.read_text())
        picture.refresh_from_db()
        self.assertEqual(picture.backend, "filer")
        self.assertIn('"status": "would_migrate"', output.getvalue())

        call_command(
            "migrate_picture_backend",
            source="filer",
            destination="finder",
            ambit="public",
            stdout=StringIO(),
        )
        picture.refresh_from_db()
        self.assertEqual(picture.backend, "finder")
        self.assertEqual(picture.picture_id, filer_image.pk)
        self.assertEqual(picture.finder_reference.image.id, migrated_image.id)

        call_command(
            "migrate_picture_backend",
            source="finder",
            destination="filer",
            ambit="public",
            stdout=StringIO(),
        )
        picture.refresh_from_db()
        self.assertEqual(picture.backend, "filer")
        self.assertEqual(picture.picture_id, filer_image.pk)
        self.assertEqual(picture.finder_reference.image.id, migrated_image.id)

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

    def test_existing_crop_is_reused(self) -> None:
        asset = get_backend("finder").resolve(
            PictureReference(backend="finder", id=str(self.image.id))
        )
        self.assertIsNotNone(asset)
        filename = asset.image.get_cropped_filename(173, 127)
        rendition_path = f"{asset.image.id}/{filename}"
        payload = get_image(image_name="cached.jpg", size=(173, 127))
        with Path(payload["path"]).open("rb") as image_file:
            asset.ambit.sample_storage.save(rendition_path, File(image_file))

        try:
            with patch.object(asset.image, "crop") as crop:
                rendition = asset.get_rendition(RenditionSpec(width=173, height=127, crop=True))
        finally:
            asset.ambit.sample_storage.delete(rendition_path)

        crop.assert_not_called()
        self.assertEqual((rendition.width, rendition.height), (173, 127))

    def test_crop_errors_are_normalized(self) -> None:
        asset = get_backend("finder").resolve(
            PictureReference(backend="finder", id=str(self.image.id))
        )
        self.assertIsNotNone(asset)

        with (
            patch.object(asset.ambit.sample_storage, "exists", return_value=False),
            patch.object(asset.image, "crop", side_effect=RuntimeError("crop failed")),
            self.assertRaises(PictureBackendError),
        ):
            asset.get_rendition(RenditionSpec(width=199, height=131, crop=True))

    def test_asset_without_crop_support_reports_a_backend_error(self) -> None:
        image = SimpleNamespace(
            pk=uuid4(),
            id=uuid4(),
            folder=self.image.folder,
            name="unsupported.bin",
            width=800,
            height=600,
            meta_data={},
            mime_type="application/octet-stream",
            sha1="unsupported",
        )
        asset = FinderImageAsset(image)

        with self.assertRaises(PictureBackendError):
            asset.get_rendition(RenditionSpec(width=100, height=100, crop=True))

    def test_svg_dimensions_are_read_from_the_rendition(self) -> None:
        asset = get_backend("finder").resolve(
            PictureReference(backend="finder", id=str(self.image.id))
        )
        self.assertIsNotNone(asset)
        rendition_path = f"{asset.image.id}/dimensions.svg"
        asset.ambit.sample_storage.save(
            rendition_path,
            ContentFile(b'<svg xmlns="http://www.w3.org/2000/svg" width="123" height="45"></svg>'),
        )

        try:
            dimensions = asset._get_dimensions(rendition_path)
        finally:
            asset.ambit.sample_storage.delete(rendition_path)

        self.assertEqual(dimensions, (123, 45))
