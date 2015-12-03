from django.test import TestCase
from django.conf import settings
from django.test.utils import override_settings
from mock import Mock, MagicMock
from djangocms_picture.cms_plugins import PicturePlugin
from djangocms_picture.models import Picture


class PicturePluginTestCase(TestCase):

    def test_plugin_returns_icon_by_default(self):
        if hasattr(settings, 'PICTURE_FULL_IMAGE_AS_ICON'):
            del settings.PICTURE_FULL_IMAGE_AS_ICON

        picture_plugin = PicturePlugin()
        mock_picture = Mock(spec=Picture)
        self.assertEqual(settings.STATIC_URL + u"cms/img/icons/plugins/image.png", picture_plugin.icon_src(mock_picture))

    @override_settings(PICTURE_FULL_IMAGE_AS_ICON=True)
    def test_plugin_returns_full_image_if_set_in_settings(self):
        picture_plugin = PicturePlugin()
        mock_picture = MagicMock()
        mock_picture.image = MagicMock()
        image_url = '/path/to/full/image.png'
        mock_picture.image.url = image_url
        self.assertEqual(image_url, picture_plugin.icon_src(mock_picture))
