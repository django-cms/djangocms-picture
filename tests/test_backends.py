from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.template import Context, Template
from django.test import SimpleTestCase, override_settings

from djangocms_picture.backends import (
    BasePictureBackend,
    PictureReference,
    RenditionSpec,
    clear_backend_cache,
    get_backend,
)
from djangocms_picture.contrib.url.backend import URLImageAsset, URLPictureBackend
from djangocms_picture.models import Picture


class MismatchedBackend(BasePictureBackend):
    alias = "different"

    def serialize(self, value: object) -> PictureReference | None:
        return None

    def resolve(self, reference: PictureReference) -> None:
        return None

    def get_asset(self, picture_instance: object) -> None:
        return None


class BackendContractTestCase(SimpleTestCase):
    def tearDown(self) -> None:
        clear_backend_cache()

    def test_reference_round_trip(self) -> None:
        reference = PictureReference(
            backend="dam",
            id="asset-42",
            context={"project": "website"},
            snapshot={"label": "Hero", "width": 1600, "height": 900},
        )

        self.assertEqual(PictureReference.from_dict(reference.as_dict()), reference)

    def test_reference_rejects_invalid_values(self) -> None:
        with self.assertRaises(TypeError):
            PictureReference.from_dict("not a mapping")
        with self.assertRaises(ValueError):
            PictureReference.from_dict({"backend": "url"})
        with self.assertRaises(ValueError):
            PictureReference.from_dict({"backend": "", "id": "image"})

    def test_default_backends_are_lazy_and_cached(self) -> None:
        backend = get_backend("url")

        self.assertIsInstance(backend, URLPictureBackend)
        self.assertIs(get_backend("url"), backend)

    def test_unknown_backend_is_rejected(self) -> None:
        with self.assertRaisesMessage(ImproperlyConfigured, 'Unknown djangocms-picture backend "missing"'):
            get_backend("missing")

    @override_settings(
        DJANGOCMS_PICTURE_BACKENDS={
            "custom": "tests.test_backends.MismatchedBackend",
        }
    )
    def test_configured_alias_must_match_backend(self) -> None:
        with self.assertRaisesMessage(ImproperlyConfigured, "does not match"):
            get_backend("custom")

    def test_url_backend_uses_original_for_every_rendition(self) -> None:
        reference = PictureReference(
            backend="url",
            id="https://example.com/image.jpg",
            snapshot={"width": 1200, "height": 800},
        )
        asset = URLImageAsset(reference)

        rendition = asset.get_rendition(RenditionSpec(width=300, height=200, crop=True))

        self.assertEqual(rendition.url, reference.id)
        self.assertEqual((rendition.width, rendition.height), (1200, 800))
        self.assertTrue(asset.capabilities.remote)
        self.assertFalse(URLPictureBackend.capabilities.responsive)

    def test_url_backend_exposes_a_url_selection_field(self) -> None:
        field = URLPictureBackend().form_field(required=False)

        self.assertIsInstance(field, forms.URLField)
        self.assertFalse(field.required)

    def test_template_tag_renders_a_backend_neutral_rendition(self) -> None:
        picture = Picture(external_picture="https://example.com/image.jpg")
        template = Template(
            "{% load djangocms_picture %}"
            "{% picture_rendition picture width=320 as rendition %}"
            "{{ rendition.url }}"
        )

        self.assertEqual(template.render(Context({"picture": picture})), picture.external_picture)

    def test_original_only_backend_does_not_generate_srcset(self) -> None:
        picture = Picture(external_picture="https://example.com/image.jpg", width=1200, height=800)
        template = Template(
            "{% load djangocms_picture %}"
            '{% picture_srcset picture widths="320,640" as sources %}'
            "{{ sources|length }}"
        )

        self.assertEqual(template.render(Context({"picture": picture})), "0")
