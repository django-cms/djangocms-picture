from collections.abc import Iterable
from typing import Any

from django.apps import AppConfig, apps
from django.core.checks import CheckMessage, Tags, Warning, register

from .backends import get_backend_aliases

FILER_CONTRIB_APP = "djangocms_picture.contrib.filer"


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
