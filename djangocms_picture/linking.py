import re
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from django.apps import apps
from django.db import models


def djangocms_link_is_enabled() -> bool:
    """Return whether djangocms-link 5+ is installed as a Django app."""

    if not apps.is_installed("djangocms_link"):
        return False
    try:
        installed_version = version("djangocms-link")
    except PackageNotFoundError:
        try:
            installed_version = str(import_module("djangocms_link").__version__)
        except (AttributeError, ImportError):
            return False
    match = re.match(r"\s*(\d+)", installed_version)
    return bool(match and int(match.group(1)) >= 5)


DJANGOCMS_LINK_ENABLED = djangocms_link_is_enabled()

if DJANGOCMS_LINK_ENABLED:
    from djangocms_link.fields import LinkField as _LinkField
else:
    _LinkField = models.JSONField


class PictureLinkField(_LinkField):
    """Stable migration field using djangocms-link's widget when available."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("default", dict)
        kwargs.setdefault("help_text", "-")
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> tuple[str | None, str, list[Any], dict[str, Any]]:
        name, _path, args, kwargs = super().deconstruct()
        return name, "djangocms_picture.linking.PictureLinkField", args, kwargs


def resolve_picture_link(value: dict[str, Any]) -> str | None:
    if not DJANGOCMS_LINK_ENABLED or not value:
        return None
    from djangocms_link.helpers import get_link

    return get_link(value)
