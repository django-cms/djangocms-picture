from importlib import import_module
from types import SimpleNamespace

from cms.api import create_page
from django.test import TestCase

from djangocms_picture.models import Picture


class PictureLinkMigrationTestCase(TestCase):
    def test_existing_external_and_internal_links_are_migrated(self) -> None:
        page = create_page("Linked page", "page.html", "en")
        external = Picture.objects.create(link_url="https://example.com/external/")
        internal = Picture.objects.create(link_page=page)
        migration = import_module("djangocms_picture.migrations.0014_picture_link")
        def get_model(app_label: str, model_name: str) -> type[Picture]:
            return Picture

        migration_apps = SimpleNamespace(get_model=get_model)

        migration.migrate_existing_links(migration_apps, schema_editor=None)
        external.refresh_from_db()
        internal.refresh_from_db()

        self.assertEqual(
            external.link,
            {"external_link": "https://example.com/external/"},
        )
        self.assertEqual(
            internal.link,
            {"internal_link": f"cms.page:{page.pk}"},
        )
