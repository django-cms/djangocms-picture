from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class PictureReference:
    """Serializable reference to an image owned by a picture backend."""

    backend: str
    id: str
    context: Mapping[str, Any] = field(default_factory=dict)
    snapshot: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "id": self.id,
            "context": dict(self.context),
            "snapshot": dict(self.snapshot),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PictureReference":
        if not isinstance(value, Mapping):
            raise TypeError("A picture reference must be a mapping.")
        try:
            backend = value["backend"]
            identifier = value["id"]
        except KeyError as error:
            raise ValueError(f"Missing picture reference key: {error.args[0]}") from error
        if not isinstance(backend, str) or not backend:
            raise ValueError("The picture reference backend must be a non-empty string.")
        if identifier is None or str(identifier) == "":
            raise ValueError("The picture reference id must not be empty.")
        return cls(
            backend=backend,
            id=str(identifier),
            context=value.get("context") or {},
            snapshot=value.get("snapshot") or {},
        )


@dataclass(frozen=True)
class ImageInfo:
    label: str
    width: int | None
    height: int | None
    alt_text: str = ""


@dataclass(frozen=True)
class RenditionSpec:
    width: int | None = None
    height: int | None = None
    crop: bool = False
    upscale: bool = False
    format: str | None = None
    quality: int | None = None


@dataclass(frozen=True)
class Rendition:
    url: str
    width: int | None
    height: int | None


@dataclass(frozen=True)
class BackendCapabilities:
    crop: bool = False
    upscale: bool = False
    responsive: bool = False
    presets: bool = False
    upload: bool = False
    refresh: bool = False
    remote: bool = False
    permanent_urls: bool = True
    formats: tuple[str, ...] = ()
