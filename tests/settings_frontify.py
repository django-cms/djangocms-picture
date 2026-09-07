from typing import Any

from .settings import *  # noqa: F403


def refresh_frontify_test_asset(
    reference: Any,
    *,
    request: Any = None,
) -> dict[str, Any] | None:
    if reference.id == "revoked":
        return None
    return {
        "id": reference.id,
        "title": "Refreshed asset",
        "width": 1200,
        "height": 800,
        "previewUrl": "https://cdn.frontify.com/refreshed.jpg",
        "downloadUrl": "https://assets.frontify.com/refreshed.jpg",
        "modifiedAt": "settings-refresh",
    }

INSTALLED_APPS = [
    *INSTALLED_APPS,  # noqa: F405
    "djangocms_picture.contrib.frontify",
]

DJANGOCMS_PICTURE_DEFAULT_BACKEND = "frontify"
DJANGOCMS_PICTURE_BACKENDS = {
    "frontify": {
        "BACKEND": "djangocms_picture.contrib.frontify.backend.FrontifyPictureBackend",
        "OPTIONS": {
            "account": "brand-library",
            "domain": "example.frontify.com",
            "client_id": "test-client",
            "allowed_hosts": ["cdn.frontify.com", "assets.frontify.com"],
            "refresher": "tests.settings_frontify.refresh_frontify_test_asset",
        },
    },
}
