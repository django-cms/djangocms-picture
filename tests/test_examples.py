from django.http import HttpRequest
from django.test import SimpleTestCase

from djangocms_picture.fields import BackendImageField, BackendSelection
from examples.standalone_backend_form import Hero, HeroForm


class StandaloneBackendFormTestCase(SimpleTestCase):
    def test_backend_field_is_declared_and_preserves_field_order(self) -> None:
        request = HttpRequest()

        form = HeroForm(request=request)

        self.assertIsInstance(HeroForm.base_fields["image"], BackendImageField)
        self.assertIsInstance(form.fields["image"], BackendImageField)
        self.assertEqual(tuple(form.fields), ("title", "image"))

    def test_form_renders_model_field_and_backend_pickers(self) -> None:
        form = HeroForm()

        html = form.as_div()

        self.assertIn('name="title"', html)
        self.assertIn('name="image_backend"', html)
        self.assertIn('name="image_filer"', html)
        self.assertIn('name="image_url"', html)
        self.assertIn('data-picture-backend-widget="filer"', html)
        self.assertIn('data-picture-backend-widget="url"', html)
        self.assertLess(html.index('name="title"'), html.index('name="image_backend"'))

    def test_serialized_selection_is_restored_as_the_initial_value(self) -> None:
        hero = Hero(
            title="Homepage",
            image_selection={
                "version": 1,
                "backend": "url",
                "value": "https://example.com/hero.jpg",
            },
        )

        form = HeroForm(instance=hero)

        selection = form.initial["image"]
        self.assertIsInstance(selection, BackendSelection)
        self.assertEqual(selection.backend.alias, "url")
        self.assertEqual(selection.value, "https://example.com/hero.jpg")

    def test_valid_selection_is_serialized_when_saved(self) -> None:
        form = HeroForm(
            data={
                "title": "Homepage",
                "image_backend": "url",
                "image_url": "https://example.com/hero.jpg",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        hero = form.save(commit=False)
        self.assertEqual(
            hero.image_selection,
            {
                "version": 1,
                "backend": "url",
                "value": "https://example.com/hero.jpg",
            },
        )

    def test_invalid_selection_is_reported_by_the_backend_field(self) -> None:
        form = HeroForm(
            data={
                "title": "Homepage",
                "image_backend": "url",
                "image_url": "not-a-url",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)
