from .settings import *  # noqa: F403

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
        },
    },
}
