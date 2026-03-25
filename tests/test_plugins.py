from cms.api import add_plugin
from cms.test_utils.testcases import CMSTestCase

from djangocms_picture.cms_plugins import PicturePlugin
from djangocms_picture.models import get_alignment

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

    def test_plugin_structure(self):
        plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=PicturePlugin.__name__,
            language=self.language,
            picture=self.picture,
        )
        self.publish(self.page, self.language)
        self.assertEqual(plugin.get_plugin_class_instance().name, "Image")

        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

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
            response = self.client.get(self.request_url)

        self.assertContains(response, 'align-right')
