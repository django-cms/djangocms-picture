# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import Picture
from .forms import PictureForm


class PicturePlugin(CMSPluginBase):
    model = Picture
    form = PictureForm
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
            classes += 'align-{} '.format(instance.alignment)
        if 'class' in instance.attributes:
            classes += '{} '.format(instance.attributes['class'])
        # we actually want to modify the class in attributes
        # this saves a simple if/else in the template
        instance.attributes['class'] = classes
        # assign link to a context variable to be performant
        context['get_link'] = instance.get_link
        context['get_size'] = instance.get_size(context, placeholder)

        return super(PicturePlugin, self).render(context, instance, placeholder)


plugin_pool.register_plugin(PicturePlugin)
