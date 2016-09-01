# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from . import models
from . import forms


class PicturePlugin(CMSPluginBase):
    model = models.Picture
    form = forms.PictureForm
    name = _('Image')
    render_template = 'djangocms_picture/picture.html'
    text_enabled = True

    fieldsets = [
        (None, {
            'fields': (
                'picture',
                'external_picture',
            )
        }),
        (_('Advanced settings'), {
            'classes': ('collapse',),
            'fields': (
                ('width', 'height'),
                'alignment',
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
        classes = ''
        if instance.alignment:
            classes += 'align-{}'.format(instance.alignment)
            if 'class' in instance.attributes:
                classes += ' {}'.format(instance.attributes['class'])
            # adapt new class
            instance.attributes['class'] = classes

        context.update({
            'instance': instance,
        })
        return context


plugin_pool.register_plugin(PicturePlugin)
