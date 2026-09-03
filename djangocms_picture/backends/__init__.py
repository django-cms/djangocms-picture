from functools import lru_cache
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from .base import BaseImageAsset, BasePictureBackend, PictureBackendError, UnsupportedBackendOperation
from .types import BackendCapabilities, ImageInfo, PictureReference, Rendition, RenditionSpec

DEFAULT_BACKENDS = {
    "filer": "djangocms_picture.contrib.filer.backend.FilerPictureBackend",
    "url": "djangocms_picture.contrib.url.backend.URLPictureBackend",
}


def get_backend_aliases() -> tuple[str, ...]:
    configured = getattr(settings, "DJANGOCMS_PICTURE_BACKENDS", {})
    aliases = dict.fromkeys((*DEFAULT_BACKENDS, *configured))
    return tuple(aliases)


def _backend_config(alias: str) -> tuple[str, dict[str, Any]]:
    configured = getattr(settings, "DJANGOCMS_PICTURE_BACKENDS", {})
    config = {**DEFAULT_BACKENDS, **configured}.get(alias)
    if config is None:
        raise ImproperlyConfigured(f'Unknown djangocms-picture backend "{alias}".')
    if isinstance(config, str):
        return config, {}
    if isinstance(config, dict) and "BACKEND" in config:
        return config["BACKEND"], config.get("OPTIONS", {})
    raise ImproperlyConfigured(
        f'DJANGOCMS_PICTURE_BACKENDS["{alias}"] must be an import path or contain a BACKEND key.'
    )


@lru_cache(maxsize=None)
def get_backend(alias: str) -> BasePictureBackend:
    path, options = _backend_config(alias)
    backend_class = import_string(path)
    backend = backend_class(**options)
    if not isinstance(backend, BasePictureBackend):
        raise ImproperlyConfigured(f'{path} must inherit from BasePictureBackend.')
    if backend.alias != alias:
        raise ImproperlyConfigured(
            f'Configured backend alias "{alias}" does not match {path}.alias "{backend.alias}".'
        )
    return backend


def get_backends() -> tuple[BasePictureBackend, ...]:
    return tuple(get_backend(alias) for alias in get_backend_aliases())


def get_backend_choices() -> tuple[tuple[str, str], ...]:
    return tuple((backend.alias, str(backend.label)) for backend in get_backends())


def clear_backend_cache() -> None:
    get_backend.cache_clear()


def get_backend_for_instance(instance: Any) -> BasePictureBackend:
    """Resolve legacy picture fields as backends without changing their storage."""

    alias = getattr(instance, "backend", None)
    if alias and alias not in {"filer", "url"}:
        return get_backend(alias)
    if alias == "url" or getattr(instance, "external_picture", None):
        return get_backend("url")
    if not alias and getattr(instance, "picture_id", None):
        alias = "filer"
    if not alias:
        alias = getattr(settings, "DJANGOCMS_PICTURE_DEFAULT_BACKEND", "filer")
    return get_backend(alias)


__all__ = [
    "BackendCapabilities",
    "BaseImageAsset",
    "BasePictureBackend",
    "ImageInfo",
    "PictureBackendError",
    "PictureReference",
    "Rendition",
    "RenditionSpec",
    "UnsupportedBackendOperation",
    "clear_backend_cache",
    "get_backend",
    "get_backend_aliases",
    "get_backend_choices",
    "get_backend_for_instance",
    "get_backends",
]
