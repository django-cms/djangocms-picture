from collections.abc import Iterable
from importlib.util import find_spec
from typing import Any

from django.apps import AppConfig, apps
from django.core.checks import CheckMessage, Error, Tags, Warning, register

from .backends import get_backend_aliases

FILER_CONTRIB_APP = "djangocms_picture.contrib.filer"
FINDER_APP = "finder"
FINDER_CONTRIB_APP = "djangocms_picture.contrib.finder"
FRONTIFY_CONTRIB_APP = "djangocms_picture.contrib.frontify"
UNSPLASH_CONTRIB_APP = "djangocms_picture.contrib.unsplash"


@register(Tags.compatibility)
def check_filer_contrib_app(
    app_configs: Iterable[AppConfig] | None = None,
    **kwargs: Any,
) -> list[CheckMessage]:
    """Warn when the default filer backend's contrib app is not installed."""

    if "filer" not in get_backend_aliases() or apps.is_installed(FILER_CONTRIB_APP):
        return []
    return [
        Warning(
            f'The django-filer backend is configured, but "{FILER_CONTRIB_APP}" '
            "is not in INSTALLED_APPS.",
            hint=(
                f'Add "{FILER_CONTRIB_APP}" to INSTALLED_APPS. In a future version, '
                "django-filer support will not be available unless this contrib app "
                "is explicitly installed."
            ),
            id="djangocms_picture.W001",
        )
    ]


@register(Tags.compatibility)
def check_finder_backend(
    app_configs: Iterable[AppConfig] | None = None,
    **kwargs: Any,
) -> list[CheckMessage]:
    """Validate the dependency and contrib app required by finder."""

    if "finder" not in get_backend_aliases():
        return []

    messages: list[CheckMessage] = []
    if find_spec(FINDER_APP) is None:
        messages.append(
            Error(
                "The django-finder backend is configured, but django-finder is not installed.",
                hint=(
                    "Install django-finder from the upstream finder branch, including the "
                    "image extras required by djangocms-picture."
                ),
                id="djangocms_picture.E001",
            )
        )
    if not apps.is_installed(FINDER_CONTRIB_APP):
        messages.append(
            Error(
                f'The django-finder backend is configured, but "{FINDER_CONTRIB_APP}" '
                "is not in INSTALLED_APPS.",
                hint=f'Add "{FINDER_CONTRIB_APP}" to INSTALLED_APPS and run migrations.',
                id="djangocms_picture.E002",
            )
        )
    return messages


@register(Tags.compatibility)
def check_frontify_backend(
    app_configs: Iterable[AppConfig] | None = None,
    **kwargs: Any,
) -> list[CheckMessage]:
    """Require Frontify's forms, static assets and commands when configured."""

    if "frontify" not in get_backend_aliases() or apps.is_installed(FRONTIFY_CONTRIB_APP):
        return []
    return [
        Error(
            f'The Frontify backend is configured, but "{FRONTIFY_CONTRIB_APP}" '
            "is not in INSTALLED_APPS.",
            hint=f'Add "{FRONTIFY_CONTRIB_APP}" to INSTALLED_APPS and run migrations.',
            id="djangocms_picture.E003",
        )
    ]


@register(Tags.compatibility)
def check_unsplash_backend(
    app_configs: Iterable[AppConfig] | None = None,
    **kwargs: Any,
) -> list[CheckMessage]:
    """Require the Unsplash picker application when configured."""

    if "unsplash" not in get_backend_aliases() or apps.is_installed(UNSPLASH_CONTRIB_APP):
        return []
    return [
        Error(
            f'The Unsplash backend is configured, but "{UNSPLASH_CONTRIB_APP}" '
            "is not in INSTALLED_APPS.",
            hint=f'Add "{UNSPLASH_CONTRIB_APP}" to INSTALLED_APPS and run migrations.',
            id="djangocms_picture.E004",
        )
    ]
