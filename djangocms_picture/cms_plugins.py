from typing import Any

from cms.plugin_base import CMSPluginBase, force_str
from cms.plugin_pool import plugin_pool
from django.conf import settings
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from .forms import PictureForm
from .models import Picture

# enable nesting of plugins inside the picture plugin
PICTURE_NESTING = getattr(settings, 'DJANGOCMS_PICTURE_NESTING', False)


class PicturePlugin(CMSPluginBase):
    model = Picture
    form = PictureForm
    name = _('Image')
    allow_children = PICTURE_NESTING
    text_enabled = True

    change_form_template = "djangocms_frontend/admin/base.html"

    fieldsets = [
        (None, {
            'fields': ('template', 'image_source'),
        }),
        (_('Attributes'), {
            'classes': ('collapse',),
            'fields': (
                'use_responsive_image',
                ('width', 'height'),
                'alignment',
                'caption_text',
                'attributes',
            )
        }),
        (_('Link'), {
            'classes': ('collapse',),
            'fields': (
                ('link_url', 'link_page'),
                'link_target',
                'link_attributes',
            )
        }),
        (_('Cropping'), {
            'classes': ('collapse',),
            'fields': (
                ('use_automatic_scaling', 'use_no_cropping'),
                ('use_crop', 'use_upscale'),
                'thumbnail_options',
            )
        })
    ]

    def get_form(
        self,
        request: HttpRequest,
        obj: Picture | None = None,
        change: bool = False,
        **kwargs: Any,
    ) -> type[PictureForm]:
        form_class = super().get_form(request, obj=obj, change=change, **kwargs)

        class RequestAwarePictureForm(form_class):
            def __init__(self, *args: Any, **form_kwargs: Any) -> None:
                form_kwargs.setdefault("request", request)
                super().__init__(*args, **form_kwargs)

        RequestAwarePictureForm.__name__ = form_class.__name__
        RequestAwarePictureForm.__qualname__ = form_class.__qualname__
        return RequestAwarePictureForm

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
        context['img_srcset_data'] = instance.img_srcset_data

        return super().render(context, instance, placeholder)

    def __str__(self):
        return force_str(super().__str__())


plugin_pool.register_plugin(PicturePlugin)
