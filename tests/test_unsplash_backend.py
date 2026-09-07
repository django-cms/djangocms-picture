import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.template.loader import get_template
from django.test import TestCase, override_settings
from django.urls import reverse

from djangocms_picture.backends import (
    PictureReference,
    RenditionSpec,
    clear_backend_cache,
    get_backend,
)
from djangocms_picture.contrib.unsplash.backend import (
    UnsplashImageAsset,
    UnsplashPictureBackend,
)
from djangocms_picture.contrib.unsplash.data import (
    UnsplashPayloadError,
    normalize_unsplash_payload,
)
from djangocms_picture.contrib.unsplash.forms import UnsplashImageChoiceField
from djangocms_picture.contrib.unsplash.widgets import UnsplashPickerWidget
from djangocms_picture.fields import BackendSelection
from djangocms_picture.forms import PictureForm
from djangocms_picture.models import Picture
from djangocms_picture.rendering import build_srcset

from .helpers import get_filer_image

UNSPLASH_PAYLOAD = {
    "id": "photo-42",
    "description": "Mountain lake at sunrise",
    "alt_description": "Snow-covered mountains reflected in a lake",
    "width": 2400,
    "height": 1600,
    "updated_at": "2026-09-01T12:00:00Z",
    "urls": {
        "raw": "https://images.unsplash.com/photo-42?ixid=required-view-token",
        "full": "https://images.unsplash.com/photo-42?ixid=required-view-token&fm=jpg&q=80",
        "small": "https://images.unsplash.com/photo-42?ixid=required-view-token&w=400",
        "thumb": "https://images.unsplash.com/photo-42?ixid=required-view-token&w=200",
    },
    "links": {
        "html": "https://unsplash.com/photos/photo-42",
        "download_location": "https://api.unsplash.com/photos/photo-42/download?ixid=tracking-token",
    },
    "user": {
        "name": "Annie Example",
        "links": {"html": "https://unsplash.com/@annie"},
    },
}

UNSPLASH_BACKENDS = {
    "unsplash": {
        "BACKEND": "djangocms_picture.contrib.unsplash.backend.UnsplashPictureBackend",
        "OPTIONS": {
            "access_key": "public-test-access-key",
            "application_name": "cms-picture-tests",
            "content_filter": "high",
            "per_page": 12,
        },
    }
}


@override_settings(
    DJANGOCMS_PICTURE_BACKENDS=UNSPLASH_BACKENDS,
    DJANGOCMS_PICTURE_DEFAULT_BACKEND="unsplash",
)
class UnsplashBackendTestCase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.staff_user = get_user_model().objects.create_user(
            username="unsplash-editor",
            password="test",
            is_staff=True,
        )

    def setUp(self) -> None:
        clear_backend_cache()

    def tearDown(self) -> None:
        clear_backend_cache()

    def test_backend_declares_remote_image_capabilities(self) -> None:
        backend = get_backend("unsplash")

        self.assertIsInstance(backend, UnsplashPictureBackend)
        self.assertTrue(backend.capabilities.remote)
        self.assertTrue(backend.capabilities.resize)
        self.assertTrue(backend.capabilities.crop)
        self.assertTrue(backend.capabilities.upscale)
        self.assertTrue(backend.capabilities.responsive)
        self.assertFalse(backend.capabilities.upload)
        self.assertTrue(backend.capabilities.permanent_urls)

    def test_backend_rejects_incomplete_or_invalid_configuration(self) -> None:
        valid = {
            "access_key": "key",
            "application_name": "example",
        }
        invalid_options = (
            ({"application_name": "example"}, "access_key"),
            ({"access_key": "key"}, "application_name"),
            ({**valid, "per_page": 0}, "per_page"),
            ({**valid, "per_page": "many"}, "per_page"),
            ({**valid, "content_filter": "none"}, "content_filter"),
            ({**valid, "orientation": "wide"}, "orientation"),
            ({**valid, "color": "chartreuse"}, "color"),
            ({**valid, "order_by": "popular"}, "order_by"),
            ({**valid, "collections": object()}, "collections"),
        )

        for options, message in invalid_options:
            with self.subTest(options=options), self.assertRaisesMessage(
                ImproperlyConfigured,
                message,
            ):
                UnsplashPictureBackend(**options)

    def test_form_renders_search_picker_and_includes_its_media(self) -> None:
        form = PictureForm()
        field = form.fields["image_source"]

        self.assertIsInstance(field.backend_fields["unsplash"], UnsplashImageChoiceField)
        self.assertEqual(form.initial["image_source"].backend, get_backend("unsplash"))
        self.assertIn("djangocms_picture/js/unsplash-picker.js", str(form.media))
        self.assertIn("djangocms_picture/css/unsplash-picker.css", str(form.media))

        html = field.widget.render(
            "image_source",
            BackendSelection(get_backend("unsplash"), UNSPLASH_PAYLOAD),
            attrs={"id": "id_image_source"},
        )
        self.assertIn('name="image_source_unsplash"', html)
        self.assertIn('data-unsplash-picker', html)
        self.assertIn(
            f'data-picker-url="{reverse("admin:djangocms_picture_unsplash_picker")}?_popup=1"',
            html,
        )
        self.assertNotIn("public-test-access-key", html)
        self.assertIn("Select Unsplash image", html)
        self.assertIn("Mountain lake at sunrise", html)
        self.assertIn("Annie Example", html)

    def test_templates_and_static_assets_are_owned_by_the_contrib_app(self) -> None:
        app_path = Path(apps.get_app_config("djangocms_picture_unsplash").path).resolve()
        template = get_template("djangocms_picture/widgets/unsplash.html")

        self.assertTrue(Path(template.origin.name).resolve().is_relative_to(app_path))
        for static_name in (
            "djangocms_picture/css/unsplash-picker.css",
            "djangocms_picture/js/unsplash-picker.js",
            "djangocms_picture/js/unsplash-popup.js",
        ):
            with self.subTest(static_name=static_name):
                static_path = finders.find(static_name)
                self.assertIsInstance(static_path, str)
                self.assertTrue(Path(static_path).resolve().is_relative_to(app_path))

    def test_picker_is_an_authenticated_django_admin_popup(self) -> None:
        url = get_backend("unsplash").get_picker_url()

        self.assertEqual(parse_qs(urlsplit(url).query), {"_popup": ["1"]})

        anonymous_response = self.client.get(url)
        self.assertEqual(anonymous_response.status_code, 302)

        self.client.force_login(self.staff_user)
        response = self.client.get(f"{url}&field_id=id_image_source_unsplash")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "djangocms_picture/admin/unsplash_picker.html",
        )
        self.assertContains(response, 'class="djangocms-picture-unsplash-popup"')
        self.assertContains(response, 'data-field-id="id_image_source_unsplash"')
        self.assertContains(response, 'data-access-key="public-test-access-key"')
        self.assertContains(response, 'name="orientation"')
        self.assertContains(response, 'name="color"')
        self.assertContains(response, 'name="order_by"')
        self.assertContains(response, "data-unsplash-focal-circle")
        self.assertContains(response, "data-unsplash-crop-mode")
        self.assertContains(response, "data-unsplash-format")
        self.assertContains(response, "data-unsplash-quality")
        self.assertContains(response, "data-unsplash-save")
        self.assertContains(response, "djangocms_picture/js/unsplash-popup.js")
        self.assertNotContains(response, '<header id="header">')
        self.assertNotContains(response, '<ol class="breadcrumbs">')
        self.assertIn("no-cache", response.headers["Cache-Control"])

    def test_custom_picker_url_preserves_query_and_adds_popup_parameter(self) -> None:
        backend = UnsplashPictureBackend(
            access_key="key",
            application_name="example",
            picker_url="/custom/picker/?tenant=one&_popup=0#results",
        )

        self.assertEqual(
            backend.get_picker_url(),
            "/custom/picker/?tenant=one&_popup=1#results",
        )

    def test_form_persists_a_normalized_snapshot(self) -> None:
        form = PictureForm(
            data={
                "image_source_backend": "unsplash",
                "image_source_unsplash": json.dumps(UNSPLASH_PAYLOAD),
                "template": "default",
                "use_responsive_image": "yes",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        picture = form.save()
        picture.refresh_from_db()
        reference = PictureReference.from_dict(picture.picture_config)

        self.assertEqual(picture.backend, "unsplash")
        self.assertIsNone(picture.picture)
        self.assertEqual(reference.id, "photo-42")
        self.assertEqual(reference.snapshot["alt_text"], UNSPLASH_PAYLOAD["alt_description"])
        self.assertEqual(reference.snapshot["attribution"]["creator_name"], "Annie Example")
        self.assertEqual(
            reference.snapshot["transform"],
            {
                "crop_mode": "entropy",
                "focal_point": {"x": 0.5, "y": 0.5},
                "format": "",
                "quality": None,
            },
        )
        self.assertIn(
            "utm_source=cms-picture-tests",
            reference.snapshot["attribution"]["creator_url"],
        )
        self.assertIn("ixid=required-view-token", reference.snapshot["raw_url"])
        self.assertEqual(picture.image_asset.info.width, 2400)

    def test_active_backend_alt_text_is_not_shadowed_by_retained_filer_image(self) -> None:
        picture = Picture.objects.create(
            backend="unsplash",
            picture=get_filer_image(),
        )
        get_backend("unsplash").set_form_value(picture, UNSPLASH_PAYLOAD, commit=True)

        self.assertEqual(picture.image_alt_text, UNSPLASH_PAYLOAD["alt_description"])

    def test_selection_serialization_round_trip_is_identical(self) -> None:
        backend = get_backend("unsplash")
        value = backend.form_field().clean(UNSPLASH_PAYLOAD)
        selection = BackendSelection(backend, value)

        serialized = json.loads(json.dumps(selection.serialize()))

        self.assertEqual(BackendSelection.deserialize(serialized), selection)

    def test_rendition_uses_supported_imgix_parameters_and_preserves_ixid(self) -> None:
        reference = get_backend("unsplash").serialize(UNSPLASH_PAYLOAD)
        self.assertIsNotNone(reference)
        asset = UnsplashImageAsset(reference)

        rendition = asset.get_rendition(
            RenditionSpec(
                width=600,
                height=300,
                crop=True,
                format="webp",
                quality=75,
            )
        )
        query = parse_qs(urlsplit(rendition.url).query)

        self.assertEqual((rendition.width, rendition.height), (600, 300))
        self.assertEqual(query["ixid"], ["required-view-token"])
        self.assertEqual(query["w"], ["600"])
        self.assertEqual(query["h"], ["300"])
        self.assertEqual(query["fit"], ["crop"])
        self.assertEqual(query["crop"], ["entropy"])
        self.assertEqual(query["fm"], ["webp"])
        self.assertEqual(query["q"], ["75"])
        self.assertIn("ixid=required-view-token", asset.get_original().url)

    def test_picker_transform_controls_unsplash_renditions(self) -> None:
        payload = {
            **UNSPLASH_PAYLOAD,
            "transform": {
                "crop_mode": "focalpoint",
                "focal_point": {"x": 0.25, "y": 0.75},
                "format": "webp",
                "quality": 68,
            },
        }
        reference = get_backend("unsplash").serialize(payload)
        self.assertIsNotNone(reference)
        asset = UnsplashImageAsset(reference)

        rendition = asset.get_rendition(
            RenditionSpec(width=600, height=300, crop=True)
        )
        query = parse_qs(urlsplit(rendition.url).query)

        self.assertEqual(query["crop"], ["focalpoint"])
        self.assertEqual(query["fp-x"], ["0.25"])
        self.assertEqual(query["fp-y"], ["0.75"])
        self.assertEqual(query["fm"], ["webp"])
        self.assertEqual(query["q"], ["68"])
        original_query = parse_qs(urlsplit(asset.get_original().url).query)
        self.assertEqual(original_query["fm"], ["webp"])
        self.assertEqual(original_query["q"], ["68"])

    def test_explicit_rendition_options_override_picker_transform(self) -> None:
        payload = {
            **UNSPLASH_PAYLOAD,
            "transform": {"format": "webp", "quality": 68},
        }
        reference = get_backend("unsplash").serialize(payload)
        self.assertIsNotNone(reference)

        rendition = UnsplashImageAsset(reference).get_rendition(
            RenditionSpec(format="jpg", quality=90)
        )
        query = parse_qs(urlsplit(rendition.url).query)

        self.assertEqual(query["fm"], ["jpg"])
        self.assertEqual(query["q"], ["90"])

    def test_rendition_dimensions_respect_upscale_setting(self) -> None:
        reference = get_backend("unsplash").serialize(UNSPLASH_PAYLOAD)
        self.assertIsNotNone(reference)
        asset = UnsplashImageAsset(reference)

        self.assertEqual(
            asset._rendition_dimensions(RenditionSpec(width=4800)),
            (2400, 1600),
        )
        self.assertEqual(
            asset._rendition_dimensions(RenditionSpec(width=4800, upscale=True)),
            (4800, 3200),
        )
        self.assertEqual(
            asset._rendition_dimensions(RenditionSpec(width=300, height=300)),
            (300, 200),
        )
        self.assertEqual(
            asset._rendition_dimensions(RenditionSpec(width=300, height=300, crop=True)),
            (300, 300),
        )

    def test_remote_asset_builds_responsive_sources(self) -> None:
        reference = get_backend("unsplash").serialize(UNSPLASH_PAYLOAD)
        self.assertIsNotNone(reference)

        sources = build_srcset(UnsplashImageAsset(reference), widths=[320, 640, 2400])

        self.assertEqual([width for width, _rendition in sources], [320, 640])
        self.assertIn("w=320", sources[0][1].url)

    def test_rendition_rejects_unsupported_options(self) -> None:
        reference = get_backend("unsplash").serialize(UNSPLASH_PAYLOAD)
        self.assertIsNotNone(reference)
        asset = UnsplashImageAsset(reference)

        with self.assertRaisesMessage(Exception, "does not support"):
            asset.get_rendition(RenditionSpec(format="gif"))
        with self.assertRaisesMessage(Exception, "between 0 and 100"):
            asset.get_rendition(RenditionSpec(quality=101))

    def test_copy_and_clear_preserve_reference_lifecycle(self) -> None:
        source = Picture.objects.create(backend="unsplash")
        target = Picture.objects.create(backend="unsplash")
        backend = get_backend("unsplash")
        backend.set_form_value(source, UNSPLASH_PAYLOAD, commit=True)

        target.copy_relations(source)
        target.refresh_from_db()
        self.assertEqual(target.picture_config, source.picture_config)

        backend.clear_reference(target, commit=True)
        target.refresh_from_db()
        self.assertEqual(target.picture_config, {})
        self.assertIsNone(target.picture)

    def test_backend_does_not_resolve_missing_or_malformed_references(self) -> None:
        backend = get_backend("unsplash")
        picture = Picture.objects.create(backend="unsplash")

        self.assertIsNone(picture.image_asset)
        self.assertIsNone(backend.resolve(PictureReference(backend="url", id="photo-42")))
        self.assertIsNone(backend.resolve(PictureReference(backend="unsplash", id="photo-42")))
        self.assertIsNone(
            backend.resolve(
                PictureReference(
                    backend="unsplash",
                    id="photo-42",
                    snapshot={**UNSPLASH_PAYLOAD, "raw_url": "https://attacker.example/photo.jpg"},
                )
            )
        )

    def test_payload_normalizer_rejects_unsafe_or_incomplete_data(self) -> None:
        invalid_payloads = (
            "not-json",
            [],
            {key: value for key, value in UNSPLASH_PAYLOAD.items() if key != "id"},
            {**UNSPLASH_PAYLOAD, "width": "wide"},
            {**UNSPLASH_PAYLOAD, "height": 0},
            {
                **UNSPLASH_PAYLOAD,
                "urls": {**UNSPLASH_PAYLOAD["urls"], "raw": "https://attacker.example/photo.jpg"},
            },
            {
                **UNSPLASH_PAYLOAD,
                "links": {
                    **UNSPLASH_PAYLOAD["links"],
                    "download_location": "https://api.unsplash.com/photos/other/download",
                },
            },
            {**UNSPLASH_PAYLOAD, "user": {}},
            {**UNSPLASH_PAYLOAD, "transform": []},
            {**UNSPLASH_PAYLOAD, "transform": {"crop_mode": "random"}},
            {
                **UNSPLASH_PAYLOAD,
                "transform": {"focal_point": {"x": -0.1, "y": 0.5}},
            },
            {**UNSPLASH_PAYLOAD, "transform": {"format": "gif"}},
            {**UNSPLASH_PAYLOAD, "transform": {"quality": 101}},
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(UnsplashPayloadError):
                normalize_unsplash_payload(
                    payload,
                    application_name="cms-picture-tests",
                )

    def test_picker_field_reports_invalid_provider_data(self) -> None:
        field = get_backend("unsplash").form_field()

        with self.assertRaises(ValidationError):
            field.clean({**UNSPLASH_PAYLOAD, "user": {}})
        self.assertIsNone(get_backend("unsplash").form_field(required=False).clean(None))

    def test_picker_widget_tolerates_malformed_initial_values(self) -> None:
        widget = UnsplashPickerWidget(
            picker_url="/admin/unsplash/",
            application_name="example",
        )

        self.assertEqual(widget.format_value({"id": "photo"}), '{"id": "photo"}')
        for value in ("not-json", ["not", "an", "object"]):
            with self.subTest(value=value):
                context = widget.get_context("image", value, attrs={})
                self.assertEqual(context["widget"]["preview_url"], "")
