import json

from django import forms
from django.test import TestCase, override_settings

from djangocms_picture.forms import PictureForm
from djangocms_picture.models import Picture

from .helpers import get_filer_image


class PictureBackendFormTestCase(TestCase):
    def test_single_template_is_a_hidden_input(self) -> None:
        form = PictureForm()

        self.assertIsInstance(form.fields["template"].widget, forms.HiddenInput)
        self.assertEqual(form.initial["template"], "default")

    @override_settings(DJANGOCMS_PICTURE_TEMPLATES=[("feature", "Feature")])
    def test_multiple_templates_use_a_select_input(self) -> None:
        form = PictureForm()

        self.assertIsInstance(form.fields["template"].widget, forms.Select)
        self.assertEqual(
            list(form.fields["template"].choices),
            [("default", "Default"), ("feature", "Feature")],
        )

    def test_form_exposes_registered_backends(self) -> None:
        form = PictureForm()

        self.assertEqual(
            list(form.fields["backend"].choices),
            [("filer", "Media library"), ("url", "External URL")],
        )
        payload = json.loads(form.fields["backend"].widget.attrs["data-picture-backends"])
        self.assertEqual(payload["filer"]["selectionField"], "picture")
        self.assertEqual(payload["url"]["selectionField"], "external_picture")
        self.assertTrue(payload["filer"]["capabilities"]["crop"])
        self.assertFalse(payload["url"]["capabilities"]["crop"])

    def test_filer_enables_picker_and_transformation_fields(self) -> None:
        form = PictureForm(instance=Picture(backend="filer"))

        self.assertFalse(form.fields["picture"].disabled)
        self.assertTrue(form.fields["external_picture"].disabled)
        self.assertFalse(form.fields["use_crop"].disabled)
        self.assertFalse(form.fields["use_upscale"].disabled)
        self.assertFalse(form.fields["use_responsive_image"].disabled)
        self.assertFalse(form.fields["thumbnail_options"].disabled)

    def test_url_enables_url_input_and_disables_transformations(self) -> None:
        form = PictureForm(
            instance=Picture(backend="url", external_picture="https://example.com/image.jpg")
        )

        self.assertTrue(form.fields["picture"].disabled)
        self.assertFalse(form.fields["external_picture"].disabled)
        self.assertTrue(form.fields["use_automatic_scaling"].disabled)
        self.assertTrue(form.fields["use_no_cropping"].disabled)
        self.assertTrue(form.fields["use_crop"].disabled)
        self.assertTrue(form.fields["use_upscale"].disabled)
        self.assertTrue(form.fields["use_responsive_image"].disabled)
        self.assertTrue(form.fields["thumbnail_options"].disabled)

    @override_settings(DJANGOCMS_PICTURE_DEFAULT_BACKEND="url")
    def test_configured_default_backend_is_used_for_new_plugins(self) -> None:
        form = PictureForm()

        self.assertEqual(form.initial["backend"], "url")
        self.assertTrue(form.fields["picture"].disabled)
        self.assertFalse(form.fields["external_picture"].disabled)

    def test_selected_backend_requires_its_picker_value(self) -> None:
        form = PictureForm(data={"backend": "url", "template": "default"})

        self.assertFalse(form.is_valid())
        self.assertIn("external_picture", form.errors)

    def test_url_selection_is_stored_by_url_backend(self) -> None:
        form = PictureForm(
            data={
                "backend": "url",
                "external_picture": "https://example.com/image.jpg",
                "template": "default",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save()
        instance.refresh_from_db()
        self.assertEqual(instance.backend, "url")
        self.assertEqual(instance.external_picture, "https://example.com/image.jpg")

    def test_switching_from_url_to_filer_clears_url_override(self) -> None:
        image = get_filer_image()
        form = PictureForm(
            data={
                "backend": "filer",
                "picture": image.pk,
                "external_picture": "https://example.com/old.jpg",
                "template": "default",
                "use_responsive_image": "inherit",
            },
            instance=Picture(backend="url", external_picture="https://example.com/old.jpg"),
        )

        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save(commit=False)
        self.assertEqual(instance.backend, "filer")
        self.assertEqual(instance.picture, image)
        self.assertIsNone(instance.external_picture)
