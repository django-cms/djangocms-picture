# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from . import models


class PicturePlugin(CMSPluginBase):
    model = models.Picture
    name = _('Picture')
    render_template = 'djangocms_picture/picture.html'
    text_enabled = True

    fieldsets = [
        (None, {
            'fields': (
                'picture',
                'alignment',
            )
        }),
        (_('Advanced settings'), {
            'classes': ('collapse',),
            'fields': (
                ('width', 'height'),
                'caption_text',
                'attributes',
            )
        }),
        (_('Link settings'), {
            'classes': ('collapse',),
            'fields': (
                ('link_url', 'link_page'),
                'link_target',
                'link_attributes',
            )
        }),
        (_('Cropping settings'), {
            'classes': ('collapse',),
            'fields': (
                ('use_automatic_scaling', 'use_no_cropping'),
                ('use_crop', 'use_upscale'),
                'use_thumbnail',
            )
        })
    ]

    def render(self, context, instance, placeholder):
        return context


plugin_pool.register_plugin(PicturePlugin)
