#!/usr/bin/env python
import os
from tempfile import mkdtemp

SECRET_KEY = "test_key"

ALLOWED_HOSTS = ["localhost"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sites",
    "django.contrib.sessions",
    "django.contrib.admin",
    "django.contrib.messages",

    "cms",
    "menus",
    "treebeard",
    'easy_thumbnails',
    'filer',

    "djangocms_picture",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join((os.path.dirname(__file__)), "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

SITE_ID=1

CMS_TEMPLATES = (
    ("page.html", "Normal page"),
)

CMS_LANGUAGES = {
    1: [{
            'code': 'en',
            'name': 'English',
        }]
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "mydatabase",
        "TEST": {
            # disable migrations when creating test database
            "MIGRATE": False,
        },
    }
}

LANGUAGE_CODE = 'en'

THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters',
)

THUMBNAIL_DEBUG =  True

CMS_CONFIRM_VERSION4 = True

DJANGOCMS_PICTURE_RESPONSIVE_IMAGES = True

DJANGOCMS_PICTURE_RESPONSIVE_IMAGES_VIEWPORT_BREAKPOINTS = [576, 768, 992]

FILE_UPLOAD_TEMP_DIR =  mkdtemp()

ROOT_URLCONF = "tests.urls"

MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
