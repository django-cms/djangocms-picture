from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from .storage import PictureSourceDescriptor
from .types import (
    BackendCapabilities,
    ImageAttribution,
    ImageInfo,
    PictureReference,
    Rendition,
    RenditionSpec,
    StoredPictureSource,
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
    stores_model_reference = False
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

    def prepare_storage(self, value: Any) -> StoredPictureSource:
        """Convert a cleaned picker value into persistent source values."""

        return StoredPictureSource(backend=self.alias, reference=self.serialize(value))

    def get_stored_reference(self, picture_instance: Any) -> PictureReference | None:
        """Read and validate the serialized reference stored on an instance."""

        source = getattr(picture_instance, "image_source", None)
        if isinstance(source, StoredPictureSource):
            reference = source.reference
        else:
            config = getattr(picture_instance, "picture_config", None)
            if not isinstance(config, Mapping) or not config:
                return None
            try:
                reference = PictureReference.from_dict(config)
            except (TypeError, ValueError):
                return None
        return reference if reference is not None and reference.backend == self.alias else None

    def get_form_value(self, picture_instance: Any) -> Any:
        """Return the backend value used to initialize its picker field."""

        reference = self.get_stored_reference(picture_instance)
        return reference.id if reference else None

    def validate_storage(self, picture_instance: Any) -> None:
        """Validate the relationship between this backend and its backing columns."""

        config = getattr(picture_instance, "picture_config", None)
        reference = None
        if config:
            if not isinstance(config, Mapping):
                raise PictureBackendError("Image source configuration must be a JSON object.")
            try:
                reference = PictureReference.from_dict(config)
            except (TypeError, ValueError) as error:
                raise PictureBackendError("Image source configuration is invalid.") from error
            if reference.backend != self.alias:
                raise PictureBackendError("Image source configuration belongs to another backend.")

        content_type_id = getattr(picture_instance, "picture_content_type_id", None)
        object_id = getattr(picture_instance, "picture_object_id", None)
        if (content_type_id is None) != (object_id is None):
            raise PictureBackendError("A model image requires both a content type and an object ID.")

        has_model_reference = content_type_id is not None
        if not self.stores_model_reference and has_model_reference:
            raise PictureBackendError(f'The "{self.alias}" backend cannot store a model image.')
        if self.stores_model_reference and reference is not None:
            if not has_model_reference:
                raise PictureBackendError(f'The "{self.alias}" backend requires a model image.')
            if str(object_id) != reference.id:
                raise PictureBackendError("The model image and serialized image IDs do not match.")

    def set_form_value(self, picture_instance: Any, value: Any, *, commit: bool = False) -> None:
        stored = self.prepare_storage(value)
        if isinstance(getattr(type(picture_instance), "image_source", None), PictureSourceDescriptor):
            picture_instance.image_source = stored
        else:
            picture_instance.backend = stored.backend
            picture_instance.picture = stored.source_object
            picture_instance.picture_config = stored.as_config()
        if commit:
            picture_instance.save(
                update_fields=(
                    "backend",
                    "picture_content_type",
                    "picture_object_id",
                    "picture_config",
                )
            )

    def copy_reference(self, source: Any, target: Any) -> None:
        """Copy this backend's selected value to an already-saved target."""

        if isinstance(
            getattr(type(target), "image_source", None),
            PictureSourceDescriptor,
        ) and isinstance(
            getattr(type(source), "image_source", None),
            PictureSourceDescriptor,
        ):
            target.image_source = source.image_source
        else:
            target.backend = self.alias
            target.picture = getattr(source, "picture", None)
            target.picture_config = dict(getattr(source, "picture_config", {}) or {})
        target.save(
            update_fields=(
                "backend",
                "picture_content_type",
                "picture_object_id",
                "picture_config",
            )
        )

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

    def validate_storage(self, picture_instance: Any) -> None:
        return None

    def copy_reference(self, source: Any, target: Any) -> None:
        return None
