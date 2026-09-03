# original from
# http://tech.octopus.energy/news/2016/01/21/testing-for-missing-migrations-in-django.html
from importlib import import_module
from io import StringIO

from django.apps import apps
from django.core.management import call_command
from django.test import TestCase, override_settings

from djangocms_picture.models import Picture


class MigrationTestCase(TestCase):

    @override_settings(MIGRATION_MODULES={})
    def test_for_missing_migrations(self):
        output = StringIO()
        options = {
            'interactive': False,
            'dry_run': True,
            'stdout': output,
            'check_changes': True,
        }

        try:
            call_command('makemigrations', 'djangocms_picture', **options)
        except SystemExit as e:
            status_code = str(e)
        else:
            # the "no changes" exit code is 0
            status_code = '0'

        if status_code == '1':
            self.fail('There are missing migrations:\n {}'.format(output.getvalue()))

    def test_external_pictures_are_assigned_to_url_backend(self) -> None:
        picture = Picture.objects.create(external_picture="https://example.com/image.jpg")
        Picture.objects.filter(pk=picture.pk).update(backend="filer")
        migration = import_module("djangocms_picture.migrations.0013_picture_backend")

        migration.select_legacy_backends(apps, None)

        picture.refresh_from_db()
        self.assertEqual(picture.backend, "url")
