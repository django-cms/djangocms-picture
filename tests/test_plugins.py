from cms.api import add_plugin
from cms.test_utils.testcases import CMSTestCase
from django.contrib import admin
from django.test import RequestFactory

from djangocms_picture.cms_plugins import PicturePlugin
from djangocms_picture.models import Picture, get_alignment

from .fixtures import TestFixture
from .helpers import get_filer_image


class PicturePluginsTestCase(TestFixture, CMSTestCase):

    def setUp(self):
        self.picture = get_filer_image()
        super().setUp()

    def tearDown(self):
        self.picture.delete()
        super().tearDown()

    def test_picture_plugin(self):
        plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=PicturePlugin.__name__,
            language=self.language,
            picture=self.picture,
        )
        plugin.full_clean()
        self.assertEqual(plugin.plugin_type, "PicturePlugin")

    def test_backend_fields_follow_template_in_the_primary_fieldset(self) -> None:
        fields = PicturePlugin.fieldsets[0][1]["fields"]

        self.assertEqual(fields, ("template", "image_source"))

    def test_admin_form_forwards_the_request_to_backend_fields(self) -> None:
        request = RequestFactory().get("/admin/")
        request.user = self.superuser
        request.session = {}
        plugin = PicturePlugin(Picture, admin.site)

        form_class = plugin.get_form(request)
        form = form_class()

        self.assertIs(form.request, request)

    def test_plugin_structure(self):
        plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=PicturePlugin.__name__,
            language=self.language,
            picture=self.picture,
        )
        self.publish(self.page, self.language)
        request_url = self.page.get_absolute_url(self.language) + "?toolbar_off=true"
        self.assertEqual(plugin.get_plugin_class_instance().name, "Image")
        self.assertIsInstance(str(plugin.get_plugin_class_instance()), str)

        with self.login_user_context(self.superuser):
            response = self.client.get(request_url)

        self.assertContains(response, 'src="/media/filer_public_thumbnails/filer_public')

        # test that alignment is added
        plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=PicturePlugin.__name__,
            language=self.language,
            picture=self.picture,
            alignment=get_alignment()[1][0],
        )
        self.publish(self.page, self.language)

        self.assertEqual(plugin.get_plugin_class_instance().name, "Image")

        with self.login_user_context(self.superuser):
            response = self.client.get(request_url)

        self.assertContains(response, 'align-right')
