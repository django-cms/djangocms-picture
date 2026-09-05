from unittest.mock import patch

from django.core import checks
from django.test import SimpleTestCase

from djangocms_picture.checks import FILER_CONTRIB_APP, check_filer_contrib_app


class PictureSystemChecksTestCase(SimpleTestCase):
    def test_filer_contrib_app_satisfies_registered_check(self) -> None:
        messages = checks.run_checks(tags=[checks.Tags.compatibility])

        self.assertNotIn("djangocms_picture.W001", {message.id for message in messages})

    def test_missing_filer_contrib_app_emits_warning(self) -> None:
        with patch("djangocms_picture.checks.apps.is_installed", return_value=False):
            messages = check_filer_contrib_app()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].id, "djangocms_picture.W001")
        self.assertEqual(
            messages[0].msg,
            f'The django-filer backend is configured, but "{FILER_CONTRIB_APP}" '
            "is not in INSTALLED_APPS.",
        )
        self.assertEqual(
            messages[0].hint,
            f'Add "{FILER_CONTRIB_APP}" to INSTALLED_APPS. In a future version, '
            "django-filer support will not be available unless this contrib app "
            "is explicitly installed.",
        )

    def test_missing_filer_contrib_app_is_ignored_without_filer_backend(self) -> None:
        with (
            patch("djangocms_picture.checks.get_backend_aliases", return_value=("url",)),
            patch("djangocms_picture.checks.apps.is_installed", return_value=False),
        ):
            messages = check_filer_contrib_app()

        self.assertEqual(messages, [])
