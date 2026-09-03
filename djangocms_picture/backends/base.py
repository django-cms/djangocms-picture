from abc import ABC, abstractmethod
from typing import Any

from .types import BackendCapabilities, ImageInfo, PictureReference, Rendition, RenditionSpec


class PictureBackendError(Exception):
    """Base exception raised by a picture backend."""


class UnsupportedBackendOperation(PictureBackendError):
    """Raised when a backend does not implement an optional capability."""


class BaseImageAsset(ABC):
    reference: PictureReference
    info: ImageInfo
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

    def set_form_value(self, picture_instance: Any, value: Any, *, commit: bool = False) -> None:
        raise UnsupportedBackendOperation(f'The "{self.alias}" backend cannot store a selected image.')

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
