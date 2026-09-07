import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from datetime import timezone as datetime_timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import get_language

from djangocms_picture.backends.types import ImageAttribution


class FrontifyPayloadError(ValueError):
    """Raised when a picker payload cannot be stored or rendered safely."""


def normalize_frontify_payload(
    value: Any,
    *,
    allowed_hosts: Sequence[str] = (),
    alt_text_field: str = "alt-tag_{language_code}",
) -> dict[str, Any]:
    """Return the render-safe subset of a Frontify Finder payload."""

    payload = _parse_payload(value)
    identifier = payload.get("id")
    if identifier is None or not str(identifier):
        raise FrontifyPayloadError("The Frontify payload does not contain an asset id.")

    expires_at = _expiry(payload.get("expires_at") or payload.get("expiresAt"))

    processing_url = _safe_url(
        payload.get("processing_url")
        or payload.get("generic_url")
        or payload.get("previewUrl")
        or payload.get("preview_url"),
        allowed_hosts=allowed_hosts,
        preserve_query=bool(expires_at),
    )
    original_url = _safe_url(
        payload.get("original_url")
        or payload.get("downloadUrl")
        or payload.get("download_url")
        or processing_url,
        allowed_hosts=allowed_hosts,
        preserve_query=bool(expires_at),
    )
    if not processing_url:
        processing_url = original_url
    if not processing_url or not original_url:
        raise FrontifyPayloadError("The Frontify payload does not contain a usable HTTPS image URL.")

    metadata = _metadata_values(payload.get("metadataValues"))
    language_code = get_language() or "en"
    metadata_key = alt_text_field.format(language_code=language_code)
    alt_text = payload.get("alt_text") or metadata.get(metadata_key) or ""
    label = payload.get("label") or payload.get("title") or payload.get("name") or str(identifier)
    focal_point = _focal_point(payload.get("focal_point") or payload.get("focalPoint"))
    attribution = ImageAttribution.from_mapping(payload.get("attribution"))
    if attribution is None:
        attribution = ImageAttribution.from_mapping(
            {
                "creator_name": payload.get("creator_name")
                or payload.get("author")
                or metadata.get("Author")
                or metadata.get("author"),
                "creator_url": payload.get("creator_url") or payload.get("author_url"),
                "copyright_notice": payload.get("copyright_notice")
                or payload.get("copyright")
                or metadata.get("Copyright")
                or metadata.get("copyright"),
                "license_name": payload.get("license_name") or payload.get("license"),
                "license_url": payload.get("license_url"),
            }
        )

    return {
        "id": str(identifier),
        "label": str(label),
        "width": _dimension(payload.get("width")),
        "height": _dimension(payload.get("height")),
        "alt_text": str(alt_text),
        "mime_type": str(payload.get("mime_type") or payload.get("media_type") or ""),
        "revision": str(
            payload.get("revision")
            or payload.get("modifiedAt")
            or payload.get("modified")
            or ""
        ),
        "processing_url": processing_url,
        "original_url": original_url,
        "focal_point": focal_point,
        "expires_at": expires_at,
        "attribution": attribution.as_dict() if attribution else {},
    }


def is_frontify_snapshot_expired(
    snapshot: Mapping[str, Any],
    *,
    at: datetime | None = None,
    leeway_seconds: int = 0,
) -> bool:
    """Return whether a normalized snapshot's signed URLs are no longer usable."""

    expires_at = _expiry(snapshot.get("expires_at") or snapshot.get("expiresAt"))
    if not expires_at:
        return False
    expiry = parse_datetime(expires_at)
    if expiry is None:
        return True
    current = at or timezone.now()
    return current.timestamp() + leeway_seconds >= expiry.timestamp()


def _parse_payload(value: Any) -> Mapping[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise FrontifyPayloadError("The Frontify picker returned invalid JSON.") from error
    if not isinstance(value, Mapping):
        raise FrontifyPayloadError("The Frontify picker must return an object.")
    return value


def _safe_url(
    value: Any,
    *,
    allowed_hosts: Sequence[str],
    preserve_query: bool = False,
) -> str:
    if not value:
        return ""
    parsed = urlsplit(str(value))
    if parsed.scheme != "https" or not parsed.hostname:
        raise FrontifyPayloadError("Frontify image URLs must use HTTPS.")
    normalized_hosts = {host.lower() for host in allowed_hosts}
    if normalized_hosts and parsed.hostname.lower() not in normalized_hosts:
        raise FrontifyPayloadError(f'Frontify image host "{parsed.hostname}" is not allowed.')
    query = parsed.query if preserve_query else ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))


def _expiry(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            parsed = datetime.fromtimestamp(value, tz=datetime_timezone.utc)
        except (OverflowError, OSError, ValueError) as error:
            raise FrontifyPayloadError("Frontify URL expiry is invalid.") from error
    elif isinstance(value, str):
        parsed = parse_datetime(value)
        if parsed is None:
            raise FrontifyPayloadError("Frontify URL expiry must be an ISO 8601 datetime.")
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, datetime_timezone.utc)
    else:
        raise FrontifyPayloadError("Frontify URL expiry must be a datetime string or timestamp.")
    return parsed.astimezone(datetime_timezone.utc).isoformat().replace("+00:00", "Z")


def _dimension(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        dimension = int(value)
    except (TypeError, ValueError) as error:
        raise FrontifyPayloadError("Frontify image dimensions must be integers.") from error
    if dimension <= 0:
        raise FrontifyPayloadError("Frontify image dimensions must be positive.")
    return dimension


def _metadata_values(value: Any) -> dict[str, Any]:
    if not isinstance(value, list):
        return {}
    metadata: dict[str, Any] = {}
    for item in value:
        if not isinstance(item, Mapping):
            continue
        field = item.get("metadataField")
        if isinstance(field, Mapping) and field.get("label"):
            metadata[str(field["label"])] = item.get("value")
    return metadata


def _focal_point(value: Any) -> list[float] | None:
    if isinstance(value, Mapping):
        value = (value.get("x"), value.get("y"))
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        x, y = (float(coordinate) for coordinate in value)
    except (TypeError, ValueError):
        return None
    if not 0 <= x <= 1 or not 0 <= y <= 1:
        return None
    return [x, y]
