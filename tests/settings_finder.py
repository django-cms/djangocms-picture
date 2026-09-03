from tempfile import mkdtemp

from .settings import *  # noqa: F403

INSTALLED_APPS = [
    *INSTALLED_APPS,  # noqa: F405
    "django.contrib.staticfiles",
    "finder",
    "finder.contrib.image.pil",
    "finder.contrib.image.svg",
    "djangocms_picture.contrib.finder",
]

FINDER_STORAGE_ROOT = mkdtemp()
FINDER_SAMPLE_STORAGE_ROOT = mkdtemp()
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "finder_public": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": FINDER_STORAGE_ROOT,
            "base_url": "/media/finder/",
            "allow_overwrite": True,
        },
    },
    "finder_public_samples": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": FINDER_SAMPLE_STORAGE_ROOT,
            "base_url": "/media/finder-samples/",
            "allow_overwrite": True,
        },
    },
}

FINDER_DEFAULT_AMBIT = "public"
DJANGOCMS_PICTURE_DEFAULT_BACKEND = "finder"
DJANGOCMS_PICTURE_BACKENDS = {
    "finder": {
        "BACKEND": "djangocms_picture.contrib.finder.backend.FinderPictureBackend",
        "OPTIONS": {"ambit": FINDER_DEFAULT_AMBIT},
    },
}
ROOT_URLCONF = "tests.urls_finder"
STATIC_URL = "/static/"
