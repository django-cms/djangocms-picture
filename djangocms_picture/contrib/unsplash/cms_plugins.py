from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.contrib import admin
from django.urls import path
from django.urls.resolvers import URLPattern
from django.utils.translation import gettext_lazy as _

from .views import UnsplashPickerView


@plugin_pool.register_plugin
class UnsplashAdminPlugin(CMSPluginBase):
    name = _("Unsplash admin endpoints")
    system = True
    render_plugin = False

    def get_plugin_urls(self) -> list[URLPattern]:
        return [
            path(
                "picker/",
                admin.site.admin_view(UnsplashPickerView.as_view()),
                name="djangocms_picture_unsplash_picker",
            )
        ]
