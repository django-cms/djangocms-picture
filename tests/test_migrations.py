from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings

from djangocms_picture.models import Picture

from .helpers import get_filer_image


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

    def test_external_picture_compatibility_property_selects_url_backend(self) -> None:
        picture = Picture.objects.create(external_picture="https://example.com/image.jpg")
        picture.refresh_from_db()

        self.assertEqual(picture.backend, "url")
        self.assertEqual(picture.external_picture, "https://example.com/image.jpg")


class GenericPictureSourceMigrationTestCase(TransactionTestCase):
    migrate_from = [
        ("djangocms_picture", "0014_picture_link"),
        ("djangocms_picture_unsplash", "0001_initial"),
    ]
    migrate_to = [
        ("djangocms_picture", "0015_generic_picture_source"),
        ("djangocms_picture_unsplash", "0002_unified_picture_storage"),
    ]

    def setUp(self) -> None:
        super().setUp()
        executor = MigrationExecutor(connection)
        migrate_from = [
            node
            for node in executor.loader.graph.leaf_nodes()
            if node[0] not in {"djangocms_picture", "djangocms_picture_unsplash"}
        ] + self.migrate_from
        executor.migrate(migrate_from)
        old_apps = executor.loader.project_state(migrate_from).apps

        Placeholder = old_apps.get_model("cms", "Placeholder")
        CMSPlugin = old_apps.get_model("cms", "CMSPlugin")
        Picture = old_apps.get_model("djangocms_picture", "Picture")
        UnsplashReference = old_apps.get_model(
            "djangocms_picture_unsplash",
            "UnsplashPictureReference",
        )

        placeholder = Placeholder.objects.create(slot="content")
        filer_image = get_filer_image(image_name="migration-source.jpg", size=(640, 480))
        filer_plugin = CMSPlugin.objects.create(
            placeholder=placeholder,
            language="en",
            plugin_type="PicturePlugin",
            position=1,
        )
        filer_picture = Picture.objects.create(
            cmsplugin_ptr=filer_plugin,
            template="default",
            backend="filer",
            picture_id=filer_image.pk,
        )
        self.filer_picture_id = filer_picture.pk
        self.filer_image_id = filer_image.pk

        url_plugin = CMSPlugin.objects.create(
            placeholder=placeholder,
            language="en",
            plugin_type="PicturePlugin",
            position=2,
        )
        url_picture = Picture.objects.create(
            cmsplugin_ptr=url_plugin,
            template="default",
            backend="filer",
            picture_id=filer_image.pk,
            external_picture="https://example.com/migrated.jpg",
        )
        self.url_picture_id = url_picture.pk

        unsplash_plugin = CMSPlugin.objects.create(
            placeholder=placeholder,
            language="en",
            plugin_type="PicturePlugin",
            position=3,
        )
        unsplash_picture = Picture.objects.create(
            cmsplugin_ptr=unsplash_plugin,
            template="default",
            backend="unsplash",
        )
        UnsplashReference.objects.create(
            picture_plugin=unsplash_picture,
            asset_id="photo-42",
            snapshot={"label": "Migrated photo", "width": 1200, "height": 800},
        )
        self.unsplash_picture_id = unsplash_picture.pk

        executor = MigrationExecutor(connection)
        migrate_to = [
            node
            for node in executor.loader.graph.leaf_nodes()
            if node[0] not in {"djangocms_picture", "djangocms_picture_unsplash"}
        ] + self.migrate_to
        executor.migrate(migrate_to)
        self.apps = executor.loader.project_state(migrate_to).apps

    def tearDown(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_sources_move_to_unified_storage(self) -> None:
        Picture = self.apps.get_model("djangocms_picture", "Picture")

        filer_picture = Picture.objects.get(pk=self.filer_picture_id)
        self.assertEqual(filer_picture.backend, "filer")
        self.assertEqual(filer_picture.picture_object_id, str(self.filer_image_id))
        self.assertEqual(filer_picture.picture_config["backend"], "filer")
        self.assertEqual(filer_picture.picture_config["id"], str(self.filer_image_id))

        url_picture = Picture.objects.get(pk=self.url_picture_id)
        self.assertEqual(url_picture.backend, "url")
        self.assertIsNone(url_picture.picture_content_type_id)
        self.assertIsNone(url_picture.picture_object_id)
        self.assertEqual(url_picture.picture_config["id"], "https://example.com/migrated.jpg")
        self.assertEqual(url_picture.picture_config["snapshot"]["width"], 640)
        self.assertEqual(url_picture.picture_config["snapshot"]["height"], 480)

        unsplash_picture = Picture.objects.get(pk=self.unsplash_picture_id)
        self.assertIsNone(unsplash_picture.picture_content_type_id)
        self.assertIsNone(unsplash_picture.picture_object_id)
        self.assertEqual(unsplash_picture.picture_config["backend"], "unsplash")
        self.assertEqual(unsplash_picture.picture_config["id"], "photo-42")
        self.assertEqual(unsplash_picture.picture_config["snapshot"]["label"], "Migrated photo")
