import json
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from djangocms_picture.backends.types import ImageAttribution


class UnsplashPayloadError(ValueError):
    """Raised when an Unsplash picker payload is incomplete or unsafe."""


def normalize_unsplash_payload(
    value: Any,
    *,
    application_name: str,
    allowed_image_hosts: Sequence[str] = ("images.unsplash.com",),
) -> dict[str, Any]:
    """Return the render-safe subset of an Unsplash photo response."""

    payload = _parse_payload(value)
    identifier = payload.get("id")
    if identifier is None or not str(identifier):
        raise UnsplashPayloadError("The Unsplash payload does not contain a photo id.")
    asset_id = str(identifier)

    urls = payload.get("urls") if isinstance(payload.get("urls"), Mapping) else {}
    links = payload.get("links") if isinstance(payload.get("links"), Mapping) else {}
    user = payload.get("user") if isinstance(payload.get("user"), Mapping) else {}
    user_links = user.get("links") if isinstance(user.get("links"), Mapping) else {}
    stored_attribution = payload.get("attribution")
    if not isinstance(stored_attribution, Mapping):
        stored_attribution = {}

    raw_url = _safe_url(
        payload.get("raw_url") or urls.get("raw"),
        allowed_hosts=allowed_image_hosts,
        description="Unsplash image",
    )
    full_url = _safe_url(
        payload.get("full_url") or urls.get("full") or raw_url,
        allowed_hosts=allowed_image_hosts,
        description="Unsplash image",
    )
    preview_url = _safe_url(
        payload.get("preview_url")
        or urls.get("small")
        or urls.get("regular")
        or full_url,
        allowed_hosts=allowed_image_hosts,
        description="Unsplash preview",
    )
    if not raw_url or not full_url or not preview_url:
        raise UnsplashPayloadError("The Unsplash payload does not contain usable image URLs.")

    download_location = _safe_url(
        payload.get("download_location") or links.get("download_location"),
        allowed_hosts=("api.unsplash.com",),
        description="Unsplash download tracking",
    )
    if urlsplit(download_location).path.rstrip("/") != f"/photos/{asset_id}/download":
        raise UnsplashPayloadError("The Unsplash download location does not match the selected photo.")

    photographer_name = stored_attribution.get("creator_name") or user.get("name")
    if not photographer_name or not str(photographer_name).strip():
        raise UnsplashPayloadError("The Unsplash payload does not identify its photographer.")
    photographer_url = _safe_url(
        stored_attribution.get("creator_url") or user_links.get("html"),
        allowed_hosts=("unsplash.com", "www.unsplash.com"),
        description="Unsplash photographer",
    )
    photo_url = _safe_url(
        stored_attribution.get("provider_url") or links.get("html"),
        allowed_hosts=("unsplash.com", "www.unsplash.com"),
        description="Unsplash photo",
    )
    if not photographer_url or not photo_url:
        raise UnsplashPayloadError("The Unsplash payload does not contain attribution links.")

    width = _dimension(payload.get("width"), "width")
    height = _dimension(payload.get("height"), "height")
    alt_text = payload.get("alt_text") or payload.get("alt_description") or payload.get("description") or ""
    label = payload.get("label") or payload.get("description") or payload.get("alt_description")
    label = label or f"Photo by {str(photographer_name).strip()}"

    attribution = ImageAttribution(
        creator_name=str(photographer_name).strip(),
        creator_url=_with_attribution_query(photographer_url, application_name),
        provider_name="Unsplash",
        provider_url=_with_attribution_query(photo_url, application_name),
    )

    return {
        "id": asset_id,
        "label": str(label),
        "width": width,
        "height": height,
        "alt_text": str(alt_text),
        "raw_url": raw_url,
        "full_url": full_url,
        "preview_url": preview_url,
        "download_location": download_location,
        "attribution": attribution.as_dict(),
        "revision": str(payload.get("revision") or payload.get("updated_at") or ""),
    }


def _parse_payload(value: Any) -> Mapping[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise UnsplashPayloadError("The Unsplash picker returned invalid JSON.") from error
    if not isinstance(value, Mapping):
        raise UnsplashPayloadError("The Unsplash picker must return an object.")
    return value


def _safe_url(
    value: Any,
    *,
    allowed_hosts: Sequence[str],
    description: str,
) -> str:
    if not value:
        return ""
    parsed = urlsplit(str(value))
    normalized_hosts = {host.lower() for host in allowed_hosts}
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.hostname.lower() not in normalized_hosts
        or parsed.username
        or parsed.password
    ):
        raise UnsplashPayloadError(f"{description} URLs must use an allowed HTTPS host.")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def _with_attribution_query(url: str, application_name: str) -> str:
    parsed = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in {"utm_source", "utm_medium"}
    ]
    query.extend((("utm_source", application_name), ("utm_medium", "referral")))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


def _dimension(value: Any, name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        dimension = int(value)
    except (TypeError, ValueError) as error:
        raise UnsplashPayloadError(f"Unsplash image {name} must be an integer.") from error
    if dimension <= 0:
        raise UnsplashPayloadError(f"Unsplash image {name} must be positive.")
    return dimension
