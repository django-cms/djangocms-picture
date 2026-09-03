from cms.api import create_page
from django.contrib.sites.models import Site
from djangocms_versioning.models import Version


class TestFixture:
    """Sets up generic setUp and tearDown methods for tests."""

    def setUp(self):
        self.language = "en"
        self.superuser = self.get_superuser()
        self.default_site = Site.objects.first()
        self.home = self.create_page(
            title="home",
            template="page.html",
        )
        self.publish(self.home, self.language)
        self.page = self.create_page(
            title="content",
            template="page.html",
        )
        self.placeholder = self.get_placeholders(self.page).get(slot="content")
        return super().setUp()

    def tearDown(self):
        self.page.delete()
        self.home.delete()
        Version.objects.all().delete()
        self.superuser.delete()

        return super().tearDown()

    def _get_version(self, grouper, version_state, language=None):
        language = language or self.language

        versions = Version.objects.filter_by_grouper(grouper).filter(state=version_state)
        for version in versions:
            if hasattr(version.content, "language") and version.content.language == language:
                return version

    def publish(self, grouper, language=None):
        from djangocms_versioning.constants import DRAFT

        version = self._get_version(grouper, DRAFT, language)
        if version is not None:
            version.publish(self.superuser)

    def unpublish(self, grouper, language=None):
        from djangocms_versioning.constants import PUBLISHED

        version = self._get_version(grouper, PUBLISHED, language)
        if version is not None:
            version.unpublish(self.superuser)

    def create_page(self, title, **kwargs):
        kwargs.setdefault("language", self.language)
        kwargs.setdefault("created_by", self.superuser)
        kwargs.setdefault("in_navigation", True)
        kwargs.setdefault("limit_visibility_in_menu", None)
        kwargs.setdefault("menu_title", title)
        return create_page(title=title, **kwargs)

    def get_placeholders(self, page):
        from cms.models import PageContent, Placeholder

        page_content = PageContent.admin_manager.latest_content().get(language=self.language, page=page)
        return Placeholder.objects.get_for_obj(page_content)
