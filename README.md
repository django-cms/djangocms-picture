djangocms-picture
=================

A picture plugin for django CMS.


Installation
------------

This plugin requires `django CMS` 3.0 or higher to be properly installed.

* In your projects `virtualenv`_, run ``pip install djangocms-picture``.
* Add ``'djangocms_picture'`` to your ``INSTALLED_APPS`` setting.
* If using Django 1.7 add ``'djangocms_picture': 'djangocms_picture.migrations_django',``
  to ``MIGRATION_MODULES``  (or define ``MIGRATION_MODULES`` if it does not exists);
  when django CMS 3.1 will be released, migrations for Django 1.7 will be moved
  to the standard location and the south-style ones to ``south_migrations``.
* Run ``manage.py migrate djangocms_picture``.


Translations
------------

If you want to help translate the plugin please do it on transifex:

https://www.transifex.com/projects/p/django-cms/resource/djangocms-picture/

