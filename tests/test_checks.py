from unittest.mock import patch

from django.core import checks
from django.test import SimpleTestCase

from djangocms_picture.checks import (
    FILER_CONTRIB_APP,
    FINDER_CONTRIB_APP,
    FRONTIFY_CONTRIB_APP,
    check_filer_contrib_app,
    check_finder_backend,
    check_frontify_backend,
)


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

    def test_finder_checks_are_ignored_without_finder_backend(self) -> None:
        with patch("djangocms_picture.checks.get_backend_aliases", return_value=("url",)):
            messages = check_finder_backend()

        self.assertEqual(messages, [])

    def test_configured_finder_requires_dependency_and_contrib_app(self) -> None:
        with (
            patch("djangocms_picture.checks.get_backend_aliases", return_value=("finder",)),
            patch("djangocms_picture.checks.find_spec", return_value=None),
            patch("djangocms_picture.checks.apps.is_installed", return_value=False),
        ):
            messages = check_finder_backend()

        self.assertEqual(
            [(message.id, message.obj) for message in messages],
            [
                ("djangocms_picture.E001", None),
                ("djangocms_picture.E002", None),
            ],
        )
        self.assertIn("django-finder is not installed", messages[0].msg)
        self.assertIn(FINDER_CONTRIB_APP, messages[1].hint)

    def test_installed_finder_satisfies_backend_checks(self) -> None:
        with (
            patch("djangocms_picture.checks.get_backend_aliases", return_value=("finder",)),
            patch("djangocms_picture.checks.find_spec", return_value=object()),
            patch("djangocms_picture.checks.apps.is_installed", return_value=True),
        ):
            messages = check_finder_backend()

        self.assertEqual(messages, [])

    def test_configured_frontify_requires_its_contrib_app(self) -> None:
        with (
            patch("djangocms_picture.checks.get_backend_aliases", return_value=("frontify",)),
            patch("djangocms_picture.checks.apps.is_installed", return_value=False),
        ):
            messages = check_frontify_backend()

        self.assertEqual([message.id for message in messages], ["djangocms_picture.E003"])
        self.assertIn(FRONTIFY_CONTRIB_APP, messages[0].hint)

    def test_frontify_check_is_satisfied_or_not_configured(self) -> None:
        with patch("djangocms_picture.checks.get_backend_aliases", return_value=("url",)):
            self.assertEqual(check_frontify_backend(), [])
        with (
            patch("djangocms_picture.checks.get_backend_aliases", return_value=("frontify",)),
            patch("djangocms_picture.checks.apps.is_installed", return_value=True),
        ):
            self.assertEqual(check_frontify_backend(), [])
