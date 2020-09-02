from cms.api import add_plugin, create_page
from cms.test_utils.testcases import CMSTestCase

from djangocms_picture.cms_plugins import PicturePlugin
from djangocms_picture.models import get_alignment

from .helpers import get_filer_image


class PicturePluginsTestCase(CMSTestCase):

    def setUp(self):
        self.picture = get_filer_image()
        self.language = "en"
        self.home = create_page(
            title="home",
            template="page.html",
            language=self.language,
        )
        self.home.publish(self.language)
        self.page = create_page(
            title="content",
            template="page.html",
            language=self.language,
        )
        self.page.publish(self.language)
        self.placeholder = self.page.placeholders.get(slot="content")
        self.superuser = self.get_superuser()

    def tearDown(self):
        self.picture.delete()
        self.home.delete()
        self.page.delete()
        self.superuser.delete()

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
        request_url = self.page.get_absolute_url(self.language) + "?toolbar_off=true"

        plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=PicturePlugin.__name__,
            language=self.language,
            picture=self.picture,
        )
        self.page.publish(self.language)
        self.assertEqual(plugin.get_plugin_class_instance().name, "Image")

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
        self.page.publish(self.language)

        self.assertEqual(plugin.get_plugin_class_instance().name, "Image")

        with self.login_user_context(self.superuser):
            response = self.client.get(request_url)

        self.assertContains(response, 'align-right')
