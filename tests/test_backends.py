from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.template import Context, Template
from django.test import SimpleTestCase, TestCase, override_settings

from djangocms_picture.backends import (
    BasePictureBackend,
    PictureReference,
    RenditionSpec,
    UnsupportedBackendOperation,
    clear_backend_cache,
    get_backend,
    get_backend_aliases,
    get_backend_for_instance,
)
from djangocms_picture.contrib.filer.backend import FilerImageAsset, FilerPictureBackend
from djangocms_picture.contrib.url.backend import URLImageAsset, URLPictureBackend
from djangocms_picture.models import Picture

from .helpers import get_filer_image


class MismatchedBackend(BasePictureBackend):
    alias = "different"

    def serialize(self, value: object) -> PictureReference | None:
        return None

    def resolve(self, reference: PictureReference) -> None:
        return None

    def get_asset(self, picture_instance: object) -> None:
        return None


class ConfiguredBackend(MismatchedBackend):
    alias = "custom"


class NotABackend:
    pass


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
        with self.assertRaises(ValueError):
            PictureReference.from_dict({"backend": "url", "id": ""})

    def test_reference_normalizes_identifier_and_empty_metadata(self) -> None:
        reference = PictureReference.from_dict(
            {"backend": "dam", "id": 42, "context": None, "snapshot": None}
        )

        self.assertEqual(reference.id, "42")
        self.assertEqual(reference.context, {})
        self.assertEqual(reference.snapshot, {})

    def test_default_backends_are_lazy_and_cached(self) -> None:
        backend = get_backend("url")

        self.assertIsInstance(backend, URLPictureBackend)
        self.assertIs(get_backend("url"), backend)

    def test_unknown_backend_is_rejected(self) -> None:
        with self.assertRaisesMessage(ImproperlyConfigured, 'Unknown djangocms-picture backend "missing"'):
            get_backend("missing")

    @override_settings(
        DJANGOCMS_PICTURE_BACKENDS={
            "custom": {
                "BACKEND": "tests.test_backends.ConfiguredBackend",
                "OPTIONS": {"library": "marketing"},
            },
        }
    )
    def test_backend_options_are_passed_to_the_backend(self) -> None:
        backend = get_backend("custom")

        self.assertEqual(backend.options, {"library": "marketing"})
        self.assertEqual(get_backend_aliases(), ("filer", "url", "custom"))

    @override_settings(DJANGOCMS_PICTURE_BACKENDS={"broken": {}})
    def test_malformed_backend_configuration_is_rejected(self) -> None:
        with self.assertRaisesMessage(ImproperlyConfigured, "must be an import path"):
            get_backend("broken")

    @override_settings(
        DJANGOCMS_PICTURE_BACKENDS={
            "broken": "tests.test_backends.NotABackend",
        }
    )
    def test_backend_must_implement_the_backend_contract(self) -> None:
        with self.assertRaisesMessage(ImproperlyConfigured, "must inherit from BasePictureBackend"):
            get_backend("broken")

    def test_optional_backend_operations_fail_explicitly(self) -> None:
        backend = MismatchedBackend()

        self.assertFalse(backend.supports_configuration_field("crop"))
        self.assertIsNone(backend.get_form_value(object()))
        with self.assertRaises(UnsupportedBackendOperation):
            backend.set_form_value(object(), "image")
        with self.assertRaises(UnsupportedBackendOperation):
            backend.form_field()
        with self.assertRaises(UnsupportedBackendOperation):
            backend.upload(object(), name="image.jpg")
        with self.assertRaises(UnsupportedBackendOperation):
            backend.refresh(PictureReference(backend="different", id="image"))

    @override_settings(
        DJANGOCMS_PICTURE_BACKENDS={
            "custom": "tests.test_backends.MismatchedBackend",
        }
    )
    def test_configured_alias_must_match_backend(self) -> None:
        with self.assertRaisesMessage(ImproperlyConfigured, "does not match"):
            get_backend("custom")

    @override_settings(DJANGOCMS_PICTURE_DEFAULT_BACKEND="url")
    def test_backend_selection_preserves_legacy_fallbacks(self) -> None:
        self.assertEqual(
            get_backend_for_instance(SimpleNamespace(backend="filer", external_picture="https://example.com/a.jpg")).alias,
            "url",
        )
        self.assertEqual(
            get_backend_for_instance(SimpleNamespace(backend="", picture_id=1)).alias,
            "filer",
        )
        self.assertEqual(
            get_backend_for_instance(SimpleNamespace(backend="", picture_id=None)).alias,
            "url",
        )

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

    def test_url_backend_serializes_and_validates_references(self) -> None:
        backend = URLPictureBackend()

        self.assertIsNone(backend.serialize(None))
        reference = backend.serialize("https://example.com/image.jpg")
        self.assertIsNotNone(reference)
        self.assertEqual(reference.id, "https://example.com/image.jpg")
        self.assertEqual(backend.resolve(reference).reference, reference)
        self.assertIsNone(backend.resolve(PictureReference(backend="filer", id=reference.id)))
        self.assertIsNone(backend.get_asset(SimpleNamespace(external_picture=None)))

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

    def test_filer_rendition_preserves_thumbnail_arguments(self) -> None:
        image = SimpleNamespace(
            pk=7,
            label="Image",
            width=800,
            height=600,
            url="/media/image.jpg",
            subject_location=(100, 200),
            default_alt_text="Alternative",
        )
        thumbnailer = MagicMock()
        thumbnailer.get_thumbnail.return_value = SimpleNamespace(
            url="/media/image_320x200.jpg",
            width=320,
            height=200,
        )

        with patch(
            "djangocms_picture.contrib.filer.backend.get_thumbnailer",
            return_value=thumbnailer,
        ):
            rendition = FilerImageAsset(image).get_rendition(
                RenditionSpec(width=320, height=200, crop=True, upscale=True)
            )

        thumbnailer.get_thumbnail.assert_called_once_with(
            {
                "size": (320, 200),
                "crop": True,
                "upscale": True,
                "subject_location": (100, 200),
            }
        )
        self.assertEqual((rendition.url, rendition.width, rendition.height), ("/media/image_320x200.jpg", 320, 200))


class FilerBackendCompatibilityTestCase(TestCase):
    def test_filer_reference_round_trip(self) -> None:
        image = get_filer_image()
        backend = FilerPictureBackend()

        reference = backend.serialize(image)

        self.assertIsNotNone(reference)
        self.assertEqual(reference.backend, "filer")
        self.assertEqual(reference.id, str(image.pk))
        self.assertEqual(backend.resolve(reference).image, image)

    def test_filer_handles_empty_stale_and_foreign_references(self) -> None:
        backend = FilerPictureBackend()

        self.assertIsNone(backend.serialize(None))
        self.assertIsNone(backend.resolve(PictureReference(backend="url", id="1")))
        self.assertIsNone(backend.resolve(PictureReference(backend="filer", id="missing")))

    def test_filer_commits_a_form_selection(self) -> None:
        image = get_filer_image()
        picture = Picture.objects.create()

        FilerPictureBackend().set_form_value(picture, image, commit=True)
        picture.refresh_from_db()

        self.assertEqual(picture.picture, image)
