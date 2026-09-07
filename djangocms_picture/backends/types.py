from dataclasses import dataclass, field
from typing import Any, ClassVar, Mapping
from urllib.parse import urlsplit


@dataclass(frozen=True)
class PictureReference:
    """Serializable reference to an image owned by a picture backend."""

    SERIALIZATION_VERSION: ClassVar[int] = 1

    backend: str
    id: str
    context: Mapping[str, Any] = field(default_factory=dict)
    snapshot: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.SERIALIZATION_VERSION,
            "backend": self.backend,
            "id": self.id,
            "context": dict(self.context),
            "snapshot": dict(self.snapshot),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PictureReference":
        if not isinstance(value, Mapping):
            raise TypeError("A picture reference must be a mapping.")
        version = value.get("version", cls.SERIALIZATION_VERSION)
        if version != cls.SERIALIZATION_VERSION:
            raise ValueError(f"Unsupported picture reference version: {version!r}.")
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
class ImageAttribution:
    """Provider-neutral creator, copyright and licence credit."""

    creator_name: str = ""
    creator_url: str = ""
    provider_name: str = ""
    provider_url: str = ""
    copyright_notice: str = ""
    license_name: str = ""
    license_url: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "creator_name",
            "provider_name",
            "copyright_notice",
            "license_name",
        ):
            object.__setattr__(
                self,
                field_name,
                str(getattr(self, field_name) or "").strip(),
            )
        for field_name in ("creator_url", "provider_url", "license_url"):
            object.__setattr__(
                self,
                field_name,
                _safe_credit_url(getattr(self, field_name)),
            )

    def as_dict(self) -> dict[str, str]:
        """Return non-empty attribution values as JSON-compatible data."""

        return {
            key: value
            for key, value in {
                "creator_name": self.creator_name,
                "creator_url": self.creator_url,
                "provider_name": self.provider_name,
                "provider_url": self.provider_url,
                "copyright_notice": self.copyright_notice,
                "license_name": self.license_name,
                "license_url": self.license_url,
            }.items()
            if value
        }

    @classmethod
    def from_mapping(cls, value: Any) -> "ImageAttribution | None":
        """Build safe attribution from provider or local metadata."""

        if not isinstance(value, Mapping):
            return None
        attribution = cls(
            creator_name=str(value.get("creator_name") or "").strip(),
            creator_url=_safe_credit_url(value.get("creator_url")),
            provider_name=str(value.get("provider_name") or "").strip(),
            provider_url=_safe_credit_url(value.get("provider_url")),
            copyright_notice=str(value.get("copyright_notice") or "").strip(),
            license_name=str(value.get("license_name") or "").strip(),
            license_url=_safe_credit_url(value.get("license_url")),
        )
        if not any(
            (
                attribution.creator_name,
                attribution.provider_name,
                attribution.copyright_notice,
                attribution.license_name,
            )
        ):
            return None
        return attribution


def _safe_credit_url(value: Any) -> str:
    if not value:
        return ""
    url = str(value).strip()
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    return url


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
    resize: bool = False
    crop: bool = False
    upscale: bool = False
    responsive: bool = False
    presets: bool = False
    upload: bool = False
    refresh: bool = False
    remote: bool = False
    permanent_urls: bool = True
    formats: tuple[str, ...] = ()
