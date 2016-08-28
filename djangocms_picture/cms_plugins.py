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

from . import models


class PicturePlugin(CMSPluginBase):
    model = models.Picture
    name = _("Picture")
    render_template = "djangocms_picture/picture.html"
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


plugin_pool.register_plugin(PicturePlugin)
