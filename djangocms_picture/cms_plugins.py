from django.utils.translation import gettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .forms import PictureForm
from .models import Picture
from .settings import PICTURE_NESTING



class PicturePlugin(CMSPluginBase):
    model = Picture
    form = PictureForm
    name = _('Image')
    allow_children = PICTURE_NESTING
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
                'template',
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
                'thumbnail_options',
            )
        }),
        (_('Responsive image settings'), {
            'classes': ('collapse',),
            'fields': (
                'use_responsive_image',
                'small_screen_viewport_width',
                'medium_screen_picture',
                'medium_screen_viewport_width',
                'large_screen_picture',
                'large_screen_viewport_width',
                'alternative_format_webp',
            )
        })
    ]

    def get_render_template(self, context, instance, placeholder):
        return 'djangocms_picture/{}/picture.html'.format(instance.template)

    def render(self, context, instance, placeholder):
        if instance.alignment:
            classes = 'align-{} '.format(instance.alignment)
            classes += instance.attributes.get('class', '')
            # Set the class attribute to include the alignment html class
            # This is done to leverage the attributes_str property
            instance.attributes['class'] = classes
        # assign link to a context variable to be performant
        context['picture_link'] = instance.get_link()
        context['picture_size'] = instance.get_size(
            width=context.get('width') or 0,
            height=context.get('height') or 0,
        )
        context['sources_data'] = instance.sources_data

        return super().render(context, instance, placeholder)


plugin_pool.register_plugin(PicturePlugin)
