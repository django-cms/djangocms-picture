#!/usr/bin/env python
from tempfile import mkdtemp


HELPER_SETTINGS = {
    'SECRET_KEY': 'test_key',
    'INSTALLED_APPS': [
        'easy_thumbnails',
        'filer',
        'mptt',
    ],
    'CMS_LANGUAGES': {
        1: [{
            'code': 'en',
            'name': 'English',
        }]
    },
    'LANGUAGE_CODE': 'en',
    'THUMBNAIL_PROCESSORS': (
        'easy_thumbnails.processors.colorspace',
        'easy_thumbnails.processors.autocrop',
        'filer.thumbnail_processors.scale_and_crop_with_subject_location',
        'easy_thumbnails.processors.filters',
    ),
    'THUMBNAIL_DEBUG': True,
    'DJANGOCMS_PICTURE_RESPONSIVE_IMAGES': True,
    'DJANGOCMS_PICTURE_RESPONSIVE_IMAGES_VIEWPORT_BREAKPOINTS': [576, 768, 992],
    'FILE_UPLOAD_TEMP_DIR': mkdtemp(),
    'DEFAULT_AUTO_FIELD': 'django.db.models.AutoField',
}


def run():
    from app_helper import runner
    runner.cms('djangocms_picture')


if __name__ == '__main__':
    run()
