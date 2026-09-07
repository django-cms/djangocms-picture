from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .types import PictureReference, StoredPictureSource


class PictureSourceDescriptor:
    """Expose the columns used for an image source as one typed value."""

    def __init__(
        self,
        *,
        backend_field: str = "backend",
        content_type_field: str = "picture_content_type",
        object_id_field: str = "picture_object_id",
        config_field: str = "picture_config",
        object_field: str = "picture",
    ) -> None:
        self.backend_field = backend_field
        self.content_type_field = content_type_field
        self.object_id_field = object_id_field
        self.config_field = config_field
        self.object_field = object_field

    @property
    def concrete_fields(self) -> tuple[str, str, str, str]:
        """Return fields that must be persisted after assigning the source."""

        return (
            self.backend_field,
            self.content_type_field,
            self.object_id_field,
            self.config_field,
        )

    def __get__(
        self,
        instance: Any | None,
        owner: type[Any] | None = None,
    ) -> StoredPictureSource | PictureSourceDescriptor:
        if instance is None:
            return self

        config = getattr(instance, self.config_field)
        reference = None
        if isinstance(config, Mapping) and config:
            try:
                reference = PictureReference.from_dict(config)
            except (TypeError, ValueError):
                pass
        return StoredPictureSource(
            backend=getattr(instance, self.backend_field),
            reference=reference,
            source_object=getattr(instance, self.object_field),
            content_type_id=getattr(instance, f"{self.content_type_field}_id"),
            object_id=getattr(instance, self.object_id_field),
        )

    def __set__(self, instance: Any, value: StoredPictureSource) -> None:
        if not isinstance(value, StoredPictureSource):
            raise TypeError("image_source must be a StoredPictureSource.")
        if value.reference is not None and value.reference.backend != value.backend:
            raise ValueError("The picture reference backend must match the stored backend.")

        setattr(instance, self.backend_field, value.backend)
        if value.source_object is not None:
            setattr(instance, self.object_field, value.source_object)
            object_id = getattr(instance, self.object_id_field)
            setattr(instance, self.object_id_field, str(object_id))
        elif value.content_type_id is not None:
            setattr(instance, f"{self.content_type_field}_id", value.content_type_id)
            setattr(instance, self.object_id_field, value.object_id)
        else:
            setattr(instance, self.object_field, None)
        setattr(instance, self.config_field, value.as_config())
