from django.http import HttpRequest
from django.test import SimpleTestCase, TestCase

from djangocms_picture.backends import PictureReference, StoredPictureSource
from djangocms_picture.fields import BackendImageField, BackendSelection
from examples.standalone_backend_form import Hero, HeroForm

from .helpers import get_filer_image


class StandaloneBackendFormTestCase(SimpleTestCase):
    def test_backend_field_is_declared_and_preserves_field_order(self) -> None:
        request = HttpRequest()

        form = HeroForm(request=request)

        self.assertIsInstance(HeroForm.base_fields["image_source"], BackendImageField)
        self.assertIsInstance(form.fields["image_source"], BackendImageField)
        self.assertEqual(tuple(form.fields), ("title", "image_source"))

    def test_form_renders_model_field_and_backend_pickers(self) -> None:
        form = HeroForm()

        html = form.as_div()

        self.assertIn('name="title"', html)
        self.assertIn('name="image_source_backend"', html)
        self.assertIn('name="image_source_filer"', html)
        self.assertIn('name="image_source_url"', html)
        self.assertIn('data-picture-backend-widget="filer"', html)
        self.assertIn('data-picture-backend-widget="url"', html)
        self.assertLess(html.index('name="title"'), html.index('name="image_source_backend"'))

    def test_serialized_selection_is_restored_as_the_initial_value(self) -> None:
        hero = Hero(title="Homepage")
        hero.image_source = StoredPictureSource(
            backend="url",
            reference=PictureReference(
                backend="url",
                id="https://example.com/hero.jpg",
            ),
        )

        form = HeroForm(instance=hero)

        selection = form.initial["image_source"]
        self.assertIsInstance(selection, BackendSelection)
        self.assertEqual(selection.backend.alias, "url")
        self.assertEqual(selection.value, "https://example.com/hero.jpg")

    def test_valid_selection_is_serialized_when_saved(self) -> None:
        form = HeroForm(
            data={
                "title": "Homepage",
                "image_source_backend": "url",
                "image_source_url": "https://example.com/hero.jpg",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        hero = form.save(commit=False)
        self.assertEqual(hero.image_backend, "url")
        self.assertIsNone(hero.image_content_type_id)
        self.assertIsNone(hero.image_object_id)
        self.assertEqual(hero.image_config["backend"], "url")
        self.assertEqual(hero.image_config["id"], "https://example.com/hero.jpg")
        self.assertEqual(hero.image_source.reference.id, "https://example.com/hero.jpg")
        self.assertEqual(hero.image_asset.get_original().url, "https://example.com/hero.jpg")
        hero.clean()

    def test_invalid_selection_is_reported_by_the_backend_field(self) -> None:
        form = HeroForm(
            data={
                "title": "Homepage",
                "image_source_backend": "url",
                "image_source_url": "not-a-url",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("image_source", form.errors)


class StandaloneModelBackendTestCase(TestCase):
    def test_filer_picker_populates_custom_generic_relation_fields(self) -> None:
        image = get_filer_image("standalone-model.jpg")
        form = HeroForm(
            data={
                "title": "Homepage",
                "image_source_backend": "filer",
                "image_source_filer": image.pk,
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        hero = form.save(commit=False)

        self.assertEqual(hero.image_backend, "filer")
        self.assertEqual(hero.image_object, image)
        self.assertEqual(hero.image_object_id, str(image.pk))
        self.assertEqual(hero.image_config["id"], str(image.pk))
        self.assertEqual(hero.image_asset.info.label, "standalone-model.jpg")
        hero.clean()
