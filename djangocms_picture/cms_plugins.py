# -*- coding: utf-8 -*-

from __future__ import unicode_literals

try:
    import urlparse
except ImportError:
    from urllib import parse as urlparse

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import Picture


class PicturePlugin(CMSPluginBase):
    model = Picture
    name = _("Picture")
    render_template = "cms/plugins/picture.html"
    text_enabled = True

    def render(self, context, instance, placeholder):
        if instance.url:
            link = instance.url
        elif instance.page_link:
            link = instance.page_link.get_absolute_url()
        else:
            link = ""
        context.update({
            'picture': instance,
            'link': link,
            'placeholder': placeholder
        })
        return context

    def icon_src(self, instance):
        if getattr(settings, 'PICTURE_FULL_IMAGE_AS_ICON', False):
            return instance.image.url
        else:
            return urlparse.urljoin(
                settings.STATIC_URL, "cms/img/icons/plugins/image.png")

plugin_pool.register_plugin(PicturePlugin)
