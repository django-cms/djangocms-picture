import json

from django import forms
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.test import TestCase, override_settings

from djangocms_picture.backends.base import BasePictureBackend
from djangocms_picture.backends.types import PictureReference
from djangocms_picture.fields import BackendImageField, BackendSelection
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
        field = form.fields["image_source"]

        self.assertEqual(
            list(field.selector_field.choices),
            [("filer", "Media library"), ("url", "External URL")],
        )
        payload = json.loads(field.widget.widgets[0].attrs["data-picture-backends"])
        self.assertTrue(payload["filer"]["capabilities"]["crop"])
        self.assertFalse(payload["url"]["capabilities"]["crop"])
        self.assertEqual(field.widget.widgets_names, ["_backend", "_filer", "_url"])

    def test_filer_picker_keeps_its_native_widget_markup(self) -> None:
        form = PictureForm()

        html = form.fields["image_source"].widget.render(
            "image_source",
            form.initial["image_source"],
            attrs={"id": "id_image_source"},
        )

        self.assertIn('class="filer-widget"', html)
        self.assertIn('class="js-related-lookup', html)
        self.assertIn('name="image_source_filer"', html)

    def test_filer_enables_transformation_fields(self) -> None:
        form = PictureForm(instance=Picture(backend="filer"))

        self.assertNotIn("picture", form.fields)
        self.assertNotIn("external_picture", form.fields)
        self.assertFalse(form.fields["use_crop"].disabled)
        self.assertFalse(form.fields["use_upscale"].disabled)
        self.assertFalse(form.fields["use_responsive_image"].disabled)
        self.assertFalse(form.fields["thumbnail_options"].disabled)

    def test_url_disables_transformations(self) -> None:
        form = PictureForm(
            instance=Picture(backend="url", external_picture="https://example.com/image.jpg")
        )

        self.assertTrue(form.fields["use_automatic_scaling"].disabled)
        self.assertTrue(form.fields["use_no_cropping"].disabled)
        self.assertTrue(form.fields["use_crop"].disabled)
        self.assertTrue(form.fields["use_upscale"].disabled)
        self.assertTrue(form.fields["use_responsive_image"].disabled)
        self.assertTrue(form.fields["thumbnail_options"].disabled)

    @override_settings(DJANGOCMS_PICTURE_DEFAULT_BACKEND="url")
    def test_configured_default_backend_is_used_for_new_plugins(self) -> None:
        form = PictureForm()

        self.assertEqual(form.initial["image_source"], BackendSelection("url", None))
        self.assertTrue(form.fields["use_crop"].disabled)

    def test_selected_backend_requires_its_picker_value(self) -> None:
        form = PictureForm(data={"image_source_backend": "url", "template": "default"})

        self.assertFalse(form.is_valid())
        self.assertIn("image_source", form.errors)

    def test_url_selection_is_stored_by_url_backend(self) -> None:
        form = PictureForm(
            data={
                "image_source_backend": "url",
                "image_source_url": "https://example.com/image.jpg",
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
                "image_source_backend": "filer",
                "image_source_filer": image.pk,
                "image_source_url": "https://example.com/old.jpg",
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

    def test_inactive_backend_value_is_not_validated(self) -> None:
        form = PictureForm(
            data={
                "image_source_backend": "url",
                "image_source_filer": "not-a-primary-key",
                "image_source_url": "https://example.com/image.jpg",
                "template": "default",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["image_source"],
            BackendSelection("url", "https://example.com/image.jpg"),
        )


class TextBackend(BasePictureBackend):
    alias = "text"
    label = "Text library"
    selection_field_name = "text_image"
    form_request: object | None = None

    def form_field(
        self,
        *,
        required: bool = True,
        request: object | None = None,
        **kwargs: object,
    ) -> forms.CharField:
        self.form_request = request
        return forms.CharField(required=required)

    def serialize(self, value: object) -> PictureReference | None:
        return None

    def resolve(self, reference: PictureReference) -> None:
        return None

    def get_asset(self, picture_instance: object) -> None:
        return None


class IntegerBackend(TextBackend):
    alias = "integer"
    label = "Integer library"
    selection_field_name = "integer_image"

    def form_field(
        self,
        *,
        required: bool = True,
        request: object | None = None,
        **kwargs: object,
    ) -> forms.IntegerField:
        return forms.IntegerField(required=required)


class BackendImageFieldTestCase(TestCase):
    def setUp(self) -> None:
        self.field = BackendImageField(backends=(TextBackend(), IntegerBackend()))

    def test_named_widget_values_are_compressed_to_a_typed_selection(self) -> None:
        data = {
            "asset_backend": "integer",
            "asset_text": "ignored",
            "asset_integer": "42",
        }

        raw_value = self.field.widget.value_from_datadict(data, {}, "asset")

        self.assertEqual(self.field.widget.widgets_names, ["_backend", "_text", "_integer"])
        self.assertEqual(self.field.clean(raw_value), BackendSelection("integer", 42))

    def test_widget_renders_named_inputs_and_only_the_selected_picker(self) -> None:
        html = self.field.widget.render(
            "asset",
            BackendSelection("integer", 42),
            attrs={"id": "id_asset"},
        )

        self.assertIn('name="asset_backend"', html)
        self.assertIn('id="id_asset_backend"', html)
        self.assertIn('name="asset_text"', html)
        self.assertIn('id="id_asset_text"', html)
        self.assertIn('name="asset_integer"', html)
        self.assertIn('id="id_asset_integer"', html)
        self.assertIn('data-picture-backend-widget="text" hidden', html)
        self.assertNotIn('data-picture-backend-widget="integer" hidden', html)

    def test_only_the_selected_backend_field_is_validated(self) -> None:
        value = ["text", "asset-id", "not-an-integer"]

        self.assertEqual(self.field.clean(value), BackendSelection("text", "asset-id"))

    def test_selected_backend_validation_errors_are_preserved(self) -> None:
        with self.assertRaises(ValidationError):
            self.field.clean(["integer", "ignored", "not-an-integer"])

    def test_widget_media_contains_the_controller(self) -> None:
        self.assertIn("djangocms_picture/js/backend-image-widget.js", self.field.widget.media._js)
        self.assertIn(
            "djangocms_picture/css/backend-image-widget.css",
            self.field.widget.media._css["all"],
        )

    def test_backend_selector_is_hidden_when_only_one_backend_is_available(self) -> None:
        field = BackendImageField(backends=(TextBackend(),))

        html = field.widget.render("asset", None, attrs={"id": "id_asset"})

        self.assertIn('class="djangocms-picture-backend-selector" hidden', html)
        self.assertIn('name="asset_backend"', html)

    def test_request_is_forwarded_to_backend_picker_fields(self) -> None:
        request = HttpRequest()
        backend = TextBackend()

        BackendImageField(backends=(backend,), request=request)

        self.assertIs(backend.form_request, request)
