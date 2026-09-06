import json
from urllib.parse import parse_qs, urlsplit

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.test import TestCase

if not apps.is_installed("djangocms_picture.contrib.frontify"):
    from unittest import SkipTest

    raise SkipTest("The Frontify contrib app is not installed.")

from djangocms_picture.backends import PictureReference, RenditionSpec, get_backend
from djangocms_picture.contrib.frontify.backend import (
    FrontifyImageAsset,
    FrontifyPictureBackend,
)
from djangocms_picture.contrib.frontify.data import (
    FrontifyPayloadError,
    normalize_frontify_payload,
)
from djangocms_picture.contrib.frontify.forms import FrontifyImageChoiceField
from djangocms_picture.contrib.frontify.models import FrontifyPictureReference
from djangocms_picture.contrib.frontify.widgets import FrontifyPickerWidget
from djangocms_picture.fields import BackendSelection
from djangocms_picture.forms import PictureForm
from djangocms_picture.models import Picture
from djangocms_picture.rendering import build_srcset

FRONTIFY_PAYLOAD = {
    "id": "asset-42",
    "title": "Campaign hero",
    "width": 1600,
    "height": 900,
    "previewUrl": "https://cdn.frontify.com/hero.jpg?preview=1",
    "downloadUrl": "https://assets.frontify.com/hero.jpg?token=discarded",
    "modifiedAt": "revision-7",
    "focalPoint": {"x": 0.25, "y": 0.75},
    "metadataValues": [
        {
            "metadataField": {"label": "alt-tag_en"},
            "value": "A campaign landscape",
        }
    ],
}


class FrontifyBackendTestCase(TestCase):
    def test_backend_declares_remote_processing_capabilities(self) -> None:
        backend = get_backend("frontify")

        self.assertIsInstance(backend, FrontifyPictureBackend)
        self.assertTrue(backend.capabilities.remote)
        self.assertTrue(backend.capabilities.resize)
        self.assertTrue(backend.capabilities.crop)
        self.assertTrue(backend.capabilities.responsive)
        self.assertFalse(backend.capabilities.upscale)
        self.assertFalse(backend.capabilities.upload)

        with self.assertRaisesMessage(ImproperlyConfigured, "allowed_hosts"):
            FrontifyPictureBackend()

    def test_form_uses_frontify_picker_and_preserves_its_media(self) -> None:
        form = PictureForm()
        field = form.fields["image_source"]

        self.assertIsInstance(field.backend_fields["frontify"], FrontifyImageChoiceField)
        self.assertEqual(form.initial["image_source"].backend, get_backend("frontify"))
        self.assertIn("@frontify/frontify-finder@2.0.1", str(form.media))
        self.assertIn("djangocms_picture/js/frontify-picker.js", str(form.media))

        html = field.widget.render(
            "image_source",
            BackendSelection(get_backend("frontify"), FRONTIFY_PAYLOAD),
            attrs={"id": "id_image_source"},
        )
        self.assertIn('data-domain="example.frontify.com"', html)
        self.assertIn('name="image_source_frontify"', html)
        self.assertIn("Campaign hero", html)

    def test_form_persists_a_normalized_snapshot(self) -> None:
        form = PictureForm(
            data={
                "image_source_backend": "frontify",
                "image_source_frontify": json.dumps(FRONTIFY_PAYLOAD),
                "template": "default",
                "use_responsive_image": "yes",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        picture = form.save()
        picture.refresh_from_db()
        extension = picture.frontify_reference

        self.assertEqual(picture.backend, "frontify")
        self.assertEqual(extension.asset_id, "asset-42")
        self.assertEqual(extension.account, "brand-library")
        self.assertEqual(extension.revision, "revision-7")
        self.assertEqual(extension.snapshot["alt_text"], "A campaign landscape")
        self.assertEqual(extension.snapshot["focal_point"], [0.25, 0.75])
        self.assertEqual(extension.snapshot["processing_url"], "https://cdn.frontify.com/hero.jpg")
        self.assertEqual(extension.snapshot["original_url"], "https://assets.frontify.com/hero.jpg")
        self.assertEqual(picture.image_asset.info.width, 1600)

    def test_selection_round_trip_restores_identical_frontify_value(self) -> None:
        field = get_backend("frontify").form_field()
        value = field.clean(FRONTIFY_PAYLOAD)
        selection = BackendSelection(get_backend("frontify"), value)

        serialized = json.loads(json.dumps(selection.serialize()))

        self.assertEqual(BackendSelection.deserialize(serialized), selection)

    def test_renditions_are_built_from_the_snapshot_without_network_access(self) -> None:
        reference = get_backend("frontify").serialize(FRONTIFY_PAYLOAD)
        self.assertIsNotNone(reference)
        asset = FrontifyImageAsset(reference)

        rendition = asset.get_rendition(
            RenditionSpec(
                width=400,
                height=300,
                crop=True,
                format="webp",
                quality=80,
            )
        )
        query = parse_qs(urlsplit(rendition.url).query)

        self.assertEqual((rendition.width, rendition.height), (400, 300))
        self.assertEqual(query["width"], ["400"])
        self.assertEqual(query["height"], ["300"])
        self.assertEqual(query["crop"], ["fp"])
        self.assertEqual(query["fp"], ["0.25,0.75"])
        self.assertEqual(query["format"], ["webp"])
        self.assertEqual(query["quality"], ["80"])
        self.assertEqual(
            asset.get_original().url,
            "https://assets.frontify.com/hero.jpg",
        )

    def test_remote_asset_builds_responsive_sources(self) -> None:
        reference = get_backend("frontify").serialize(FRONTIFY_PAYLOAD)
        self.assertIsNotNone(reference)

        sources = build_srcset(
            FrontifyImageAsset(reference),
            widths=[320, 640, 1600],
        )

        self.assertEqual([width for width, _ in sources], [320, 640])
        self.assertIn("width=320", sources[0][1].url)

    def test_rendition_rejects_unsupported_options(self) -> None:
        reference = get_backend("frontify").serialize(FRONTIFY_PAYLOAD)
        self.assertIsNotNone(reference)
        asset = FrontifyImageAsset(reference)

        with self.assertRaisesMessage(Exception, "upscaling"):
            asset.get_rendition(RenditionSpec(width=400, upscale=True))
        with self.assertRaisesMessage(Exception, "does not support"):
            asset.get_rendition(RenditionSpec(format="gif"))
        with self.assertRaisesMessage(Exception, "between 0 and 100"):
            asset.get_rendition(RenditionSpec(quality=101))

    def test_picker_rejects_insecure_and_untrusted_urls(self) -> None:
        field = get_backend("frontify").form_field()

        for url in (
            "http://cdn.frontify.com/hero.jpg",
            "https://attacker.example/hero.jpg",
        ):
            payload = {**FRONTIFY_PAYLOAD, "previewUrl": url}
            with self.subTest(url=url), self.assertRaises(ValidationError):
                field.clean(payload)

    def test_snapshot_normalizer_rejects_malformed_provider_data(self) -> None:
        invalid_payloads = (
            "not-json",
            [],
            {"previewUrl": "https://cdn.frontify.com/image.jpg"},
            {"id": "asset"},
            {**FRONTIFY_PAYLOAD, "width": "wide"},
            {**FRONTIFY_PAYLOAD, "height": 0},
            {
                **FRONTIFY_PAYLOAD,
                "downloadUrl": "http://assets.frontify.com/image.jpg",
            },
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(FrontifyPayloadError):
                normalize_frontify_payload(
                    payload,
                    allowed_hosts=("cdn.frontify.com", "assets.frontify.com"),
                )

    def test_snapshot_normalizer_accepts_v1_fields_and_ignores_bad_focal_data(self) -> None:
        snapshot = normalize_frontify_payload(
            {
                "id": 7,
                "name": "Legacy image",
                "generic_url": "https://cdn.frontify.com/legacy.jpg?width=20",
                "download_url": "https://assets.frontify.com/legacy.jpg",
                "focal_point": [2, "invalid"],
                "metadataValues": [None, {"metadataField": None}],
            },
            allowed_hosts=("cdn.frontify.com", "assets.frontify.com"),
        )

        self.assertEqual(snapshot["id"], "7")
        self.assertEqual(snapshot["processing_url"], "https://cdn.frontify.com/legacy.jpg")
        self.assertIsNone(snapshot["focal_point"])
        self.assertIsNone(snapshot["width"])

    def test_rendition_dimensions_preserve_source_aspect_ratio(self) -> None:
        reference = get_backend("frontify").serialize(FRONTIFY_PAYLOAD)
        self.assertIsNotNone(reference)
        asset = FrontifyImageAsset(reference)

        self.assertEqual(
            asset._rendition_dimensions(RenditionSpec(width=400)),
            (400, 225),
        )
        self.assertEqual(
            asset._rendition_dimensions(RenditionSpec(height=225)),
            (400, 225),
        )
        self.assertEqual(
            asset._rendition_dimensions(RenditionSpec(width=600, height=300)),
            (533, 300),
        )
        self.assertEqual(
            asset._rendition_dimensions(RenditionSpec()),
            (1600, 900),
        )

        unknown_size = FrontifyImageAsset(
            PictureReference(
                backend="frontify",
                id="unknown",
                snapshot={
                    "processing_url": "https://cdn.frontify.com/unknown.jpg",
                    "original_url": "https://assets.frontify.com/unknown.jpg",
                },
            )
        )
        self.assertEqual(
            unknown_size._rendition_dimensions(RenditionSpec(width=300)),
            (300, None),
        )

    def test_picker_widget_tolerates_unbound_and_malformed_initial_values(self) -> None:
        widget = FrontifyPickerWidget(
            domain="example.frontify.com",
            client_id="client",
            finder_script_url="https://example.com/finder.js",
        )

        self.assertEqual(widget.format_value("raw"), "raw")
        self.assertEqual(widget.format_value({"value": 1}), '{"value": 1}')
        for value in ("not-json", ["not", "an", "object"]):
            with self.subTest(value=value):
                context = widget.get_context("image", value, attrs={})
                self.assertEqual(context["widget"]["preview_url"], "")

    def test_optional_picker_accepts_an_empty_value(self) -> None:
        field = get_backend("frontify").form_field(required=False)

        self.assertIsNone(field.clean(None))

    def test_backend_resolves_only_active_snapshot_references(self) -> None:
        backend = get_backend("frontify")

        self.assertIsNone(backend.resolve(PictureReference(backend="url", id="asset-42")))
        self.assertIsNone(backend.resolve(PictureReference(backend="frontify", id="asset-42")))
        self.assertIsNone(
            backend.resolve(
                PictureReference(
                    backend="frontify",
                    id="asset-42",
                    snapshot={"disabled": True},
                )
            )
        )
        self.assertIsNone(
            backend.resolve(
                PictureReference(
                    backend="frontify",
                    id="asset-42",
                    snapshot={"id": "asset-42", "processing_url": "https://attacker.example/a.jpg"},
                )
            )
        )

    def test_copy_and_clear_preserve_snapshot_lifecycle(self) -> None:
        source = Picture.objects.create(backend="frontify")
        target = Picture.objects.create(backend="frontify")
        backend = get_backend("frontify")
        backend.set_form_value(source, FRONTIFY_PAYLOAD, commit=True)

        target.copy_relations(source)
        target.refresh_from_db()
        self.assertEqual(target.frontify_reference.snapshot, source.frontify_reference.snapshot)

        backend.clear_reference(target, commit=True)
        self.assertFalse(
            FrontifyPictureReference.objects.filter(picture_plugin=target).exists()
        )

    def test_disabled_or_missing_extensions_do_not_render(self) -> None:
        picture = Picture.objects.create(backend="frontify")
        self.assertIsNone(picture.image_asset)

        backend = get_backend("frontify")
        backend.set_form_value(picture, FRONTIFY_PAYLOAD, commit=True)
        FrontifyPictureReference.objects.filter(picture_plugin=picture).update(disabled=True)
        picture.refresh_from_db()

        self.assertIsNone(picture.image_asset)
