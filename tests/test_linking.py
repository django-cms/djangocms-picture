from importlib.metadata import PackageNotFoundError
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from djangocms_picture.linking import djangocms_link_is_enabled


class DjangocmsLinkDetectionTestCase(SimpleTestCase):
    @patch("djangocms_picture.linking.apps.is_installed", return_value=False)
    def test_disabled_when_app_is_not_installed(self, is_installed: object) -> None:
        self.assertFalse(djangocms_link_is_enabled())

    @patch("djangocms_picture.linking.version", return_value="4.9.0")
    @patch("djangocms_picture.linking.apps.is_installed", return_value=True)
    def test_disabled_before_version_five(
        self,
        is_installed: object,
        installed_version: object,
    ) -> None:
        self.assertFalse(djangocms_link_is_enabled())

    @patch("djangocms_picture.linking.version", return_value="5.0.0a1")
    @patch("djangocms_picture.linking.apps.is_installed", return_value=True)
    def test_enabled_from_version_five(
        self,
        is_installed: object,
        installed_version: object,
    ) -> None:
        self.assertTrue(djangocms_link_is_enabled())

    @patch(
        "djangocms_picture.linking.import_module",
        return_value=SimpleNamespace(__version__="5.1.0"),
    )
    @patch("djangocms_picture.linking.version", side_effect=PackageNotFoundError)
    @patch("djangocms_picture.linking.apps.is_installed", return_value=True)
    def test_module_version_is_used_without_package_metadata(
        self,
        is_installed: object,
        installed_version: object,
        import_link: object,
    ) -> None:
        self.assertTrue(djangocms_link_is_enabled())
