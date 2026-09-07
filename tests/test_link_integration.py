from unittest.mock import patch

import pytest
from cms.api import create_page
from django.apps import apps
from django.test import TestCase

if not apps.is_installed("djangocms_link"):
    pytest.skip("djangocms-link is not installed as a Django app", allow_module_level=True)

pytest.importorskip("djangocms_link", minversion="5")

from djangocms_link.fields import LinkField, LinkFormField

from djangocms_picture.cms_plugins import PicturePlugin
from djangocms_picture.forms import PictureForm
from djangocms_picture.linking import DJANGOCMS_LINK_ENABLED
from djangocms_picture.models import Picture

from .helpers import get_filer_image


class DjangocmsLinkIntegrationTestCase(TestCase):
    def test_model_and_admin_use_djangocms_link(self) -> None:
        self.assertTrue(DJANGOCMS_LINK_ENABLED)
        self.assertIsInstance(Picture._meta.get_field("link"), LinkField)

        form = PictureForm(instance=Picture(link_url="https://example.com/legacy/"))

        self.assertIsInstance(form.fields["link"], LinkFormField)
        self.assertNotIn("link_url", form.fields)
        self.assertNotIn("link_page", form.fields)
        self.assertEqual(form.initial["link"], {"external_link": "https://example.com/legacy/"})
        self.assertEqual(
            PicturePlugin.fieldsets[-1][1]["fields"],
            ("link", "link_target", "link_attributes"),
        )
        self.assertIn('class="link-widget widget"', form["link"].as_widget())

    def test_form_saves_link_and_mirrors_safe_legacy_url(self) -> None:
        image = get_filer_image()
        unbound_form = PictureForm()
        external_position = unbound_form.fields["link"].widget.data_pos["external_link"]
        form = PictureForm(
            data={
                "image_source_backend": "filer",
                "image_source_filer": image.pk,
                "template": "default",
                "use_responsive_image": "inherit",
                "link_0": "external_link",
                f"link_{external_position}": "https://example.com/new/",
            },
            instance=Picture(link_url="https://example.com/legacy/"),
        )

        self.assertTrue(form.is_valid(), form.errors)
        picture = form.save()
        picture.refresh_from_db()

        self.assertEqual(picture.link, {"external_link": "https://example.com/new/"})
        self.assertEqual(picture.link_url, "https://example.com/new/")
        self.assertIsNone(picture.link_page_id)
        self.assertEqual(picture.get_link(), "https://example.com/new/")

    def test_legacy_mirror_supports_cms_pages_but_not_other_link_types(self) -> None:
        page = create_page("Mirrored page", "page.html", "en")
        picture = Picture.objects.create(link={"internal_link": f"cms.page:{page.pk}"})

        self.assertEqual(picture.link_page_id, page.pk)
        self.assertIsNone(picture.link_url)

        picture.link = {"external_link": "mailto:editor@example.com"}
        picture.save(update_fields=("link",))
        picture.refresh_from_db()
        self.assertIsNone(picture.link_url)
        self.assertIsNone(picture.link_page_id)

        picture.link = {"file_link": "filer.file:1"}
        picture.sync_legacy_link_fields()
        self.assertIsNone(picture.link_url)
        self.assertIsNone(picture.link_page_id)

        picture.link = {"internal_link": "cms.page:999999"}
        picture.sync_legacy_link_fields()
        self.assertIsNone(picture.link_page_id)

    def test_internal_link_resolves_through_djangocms_link(self) -> None:
        page = create_page("Linked page", "page.html", "en")
        picture = Picture(
            language="en",
            link={"internal_link": f"cms.page:{page.pk}"},
        )

        with patch(
            "djangocms_link.helpers.get_obj_link",
            return_value="/linked-page/",
        ) as get_obj_link:
            self.assertEqual(picture.get_link(), "/linked-page/")

        self.assertEqual(get_obj_link.call_args.args[0], page)
