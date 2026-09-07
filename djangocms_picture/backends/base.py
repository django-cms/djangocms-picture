from abc import ABC, abstractmethod
from typing import Any

from .types import (
    BackendCapabilities,
    ImageAttribution,
    ImageInfo,
    PictureReference,
    Rendition,
    RenditionSpec,
)


class PictureBackendError(Exception):
    """Base exception raised by a picture backend."""


class UnsupportedBackendOperation(PictureBackendError):
    """Raised when a backend does not implement an optional capability."""


class BaseImageAsset(ABC):
    reference: PictureReference
    info: ImageInfo
    attribution: ImageAttribution | None = None
    capabilities = BackendCapabilities()

    @abstractmethod
    def get_original(self) -> Rendition:
        raise NotImplementedError

    @abstractmethod
    def get_rendition(self, spec: RenditionSpec) -> Rendition:
        raise NotImplementedError


class BasePictureBackend(ABC):
    alias: str
    label: str
    selection_field_name: str
    configuration_fields: frozenset[str] = frozenset()
    capabilities = BackendCapabilities()

    def __init__(self, **options: Any) -> None:
        self.options = options

    @abstractmethod
    def serialize(self, value: Any) -> PictureReference | None:
        raise NotImplementedError

    @abstractmethod
    def resolve(self, reference: PictureReference) -> BaseImageAsset | None:
        raise NotImplementedError

    @abstractmethod
    def get_asset(self, picture_instance: Any) -> BaseImageAsset | None:
        raise NotImplementedError

    def supports_configuration_field(self, field_name: str) -> bool:
        return field_name in self.configuration_fields

    def get_form_value(self, picture_instance: Any) -> Any:
        """Return the backend value used to initialize its picker field."""

        asset = self.get_asset(picture_instance)
        return asset.reference.id if asset else None

    def set_form_value(self, picture_instance: Any, value: Any, *, commit: bool = False) -> None:
        raise UnsupportedBackendOperation(f'The "{self.alias}" backend cannot store a selected image.')

    def copy_reference(self, source: Any, target: Any) -> None:
        """Copy this backend's selected value to an already-saved target."""

        raise UnsupportedBackendOperation(f'The "{self.alias}" backend cannot copy image references.')

    def clear_reference(self, picture_instance: Any, *, commit: bool = False) -> None:
        """Remove this backend's selected value from a picture instance."""

        self.set_form_value(picture_instance, None, commit=commit)

    def form_field(self, *, required: bool = True, request: Any = None, **kwargs: Any) -> Any:
        raise UnsupportedBackendOperation(f'The "{self.alias}" backend does not provide a form field.')

    def upload(
        self,
        file: Any,
        *,
        name: str,
        user: Any = None,
        context: dict[str, Any] | None = None,
    ) -> PictureReference:
        raise UnsupportedBackendOperation(f'The "{self.alias}" backend does not support uploads.')

    def refresh(self, reference: PictureReference, *, request: Any = None) -> PictureReference:
        raise UnsupportedBackendOperation(f'The "{self.alias}" backend does not support refreshes.')


class UnavailablePictureBackend(BasePictureBackend):
    """Read-only marker for a persisted backend alias no longer configured."""

    label = "Unavailable image source"
    selection_field_name = ""
    configuration_fields: frozenset[str] = frozenset()
    capabilities = BackendCapabilities()

    def __init__(self, alias: str) -> None:
        super().__init__()
        self.alias = alias

    def serialize(self, value: Any) -> None:
        return None

    def resolve(self, reference: PictureReference) -> None:
        return None

    def get_asset(self, picture_instance: Any) -> None:
        return None

    def copy_reference(self, source: Any, target: Any) -> None:
        return None
