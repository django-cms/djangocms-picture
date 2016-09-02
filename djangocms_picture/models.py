# -*- coding: utf-8 -*-
"""
Enables the user to add an "Image" plugin that displays an image
using the HTML <img> tag.
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext, ugettext_lazy as _

from cms.models import CMSPlugin
from cms.models.fields import PageField

from djangocms_attributes_field.fields import AttributesField

from filer.models import ThumbnailOption
from filer.fields.image import FilerImageField


# add setting for picture alignment, renders a class or inline styles
# depending on your template setup
PICTURE_ALIGNMENT = getattr(
    settings,
    'DJANGOCMS_PICTURE_ALIGN',
    (
        ('left', _('Align left')),
        ('right', _('Align right')),
        ('left', _('Align center')),
    )
)

# use golden ration as default (https://en.wikipedia.org/wiki/Golden_ratio)
PICTURE_RATIO = getattr(settings, 'DJANGOCMS_PICTURE_RATIO', 1.6180)

LINK_TARGET = (
    ('_blank', _('Open in new window.')),
    ('_self', _('Open in same window.')),
    ('_parent', _('Delegate to parent.')),
    ('_top', _('Delegate to top.')),
)


@python_2_unicode_compatible
class Picture(CMSPlugin):
    """
    Renders an image with the option of adding a link
    """
    picture = FilerImageField(
        verbose_name=_('Image'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    external_picture = models.URLField(
        verbose_name=_('External image'),
        blank=True,
        max_length=255,
        help_text=_('If provided, overrides the embedded image. '
            'Certain options such as cropping are not applicable for external images.')
    )
    width = models.PositiveIntegerField(
        verbose_name=_('Width'),
        blank=True,
        null=True,
        help_text=_('The image width as number in pixels. '
            'Example: "720" and not "720px".'),
    )
    height = models.PositiveIntegerField(
        verbose_name=_('Height'),
        blank=True,
        null=True,
        help_text=_('The image height as number in pixels. '
            'Example: "720" and not "720px".'),
    )
    alignment = models.CharField(
        verbose_name=_('Alignment'),
        choices=PICTURE_ALIGNMENT,
        blank=True,
        max_length=255,
        help_text=_('Aligns the image to the selected option.'),
    )
    caption_text = models.TextField(
        verbose_name=_('Caption text'),
        blank=True,
        help_text=_('Provide a description, attribution, copyright or other information.')
    )
    attributes = AttributesField(
        verbose_name=_('Attributes'),
        blank=True,
        excluded_keys=['src', 'width', 'height'],
    )
    # link models
    link_url = models.URLField(
        verbose_name=_('External URL'),
        blank=True,
        max_length=255,
        help_text=_('Wraps the image in a link to an external URL.'),
    )
    link_page = PageField(
        verbose_name=_('Internal URL'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text=_('Wraps the image in a link to an internal (page) URL.'),
    )
    link_target = models.CharField(
        verbose_name=_('Link target'),
        choices=LINK_TARGET,
        blank=True,
        max_length=255,
    )
    link_attributes = AttributesField(
        verbose_name=_('Link attributes'),
        blank=True,
        excluded_keys=['href', 'target'],
    )
    # cropping models
    # active per default
    use_automatic_scaling = models.BooleanField(
        verbose_name=_('Automatic scaling'),
        blank=True,
        default=True,
        help_text=_('Uses the placeholder dimenstions to automatically calculate the size.'),
    )
    # ignores all other cropping options
    # throws validation error if other cropping options are selected
    use_no_cropping = models.BooleanField(
        verbose_name=_('Use original image.'),
        blank=True,
        default=False,
        help_text=_('Outputs the raw image without cropping.'),
    )
    # upscale and crop work together
    # throws validation error if other cropping options are selected
    use_crop = models.BooleanField(
        verbose_name=_('Crop image'),
        blank=True,
        default=False,
        help_text=_('Crops the image according to the given thumbnail settings in the template.'),
    )
    use_upscale = models.BooleanField(
        verbose_name=_('Upscale image'),
        blank=True,
        default=False,
        help_text=_('Upscales the image to the size of the thumbnail settings in the template.')
    )
    # overrides all other options
    # throws validation error if other cropping options are selected
    use_thumbnail = models.ForeignKey(
        ThumbnailOption,
        verbose_name=_('Thumbnail options'),
        blank=True,
        null=True,
        help_text=_('Overrides width, height, crop and upscale with the provided preset.'),
    )

    # Add an app namespace to related_name to avoid field name clashes
    # with any other plugins that have a field with the same name as the
    # lowercase of the class name of this model.
    # https://github.com/divio/django-cms/issues/5030
    cmsplugin_ptr = models.OneToOneField(
        CMSPlugin,
        related_name='%(app_label)s_%(class)s',
        parent_link=True,
    )

    def __str__(self):
        if self.picture and self.picture.label:
            return self.picture.label
        return str(self.pk)

    def get_short_description(self):
        if self.picture and self.picture.label:
            return self.picture.label
        if self.link_url:
            return self.link_url
        return ugettext('<file is missing>')

    def copy_relations(self, oldinstance):
        # Because we have a ForeignKey, it's required to copy over
        # the reference from the instance to the new plugin.
        self.picture = oldinstance.picture

    def get_size(self, context, placeholder):
        crop = self.use_crop or False
        upscale = self.use_upscale or False
        # use field thumbnail settings
        if self.use_thumbnail:
            width = self.use_thumbnail.width
            height = self.use_thumbnail.height
            crop = self.use_thumbnail.crop
            upscale = self.use_thumbnail.upscale
        elif self.use_automatic_scaling:
            width = context.get('width', None)
            height = context.get('height', None)
        else:
            width = self.width or None
            height = self.height or None

        # calculate height when not given according to the
        # golden ratio
        if not height and width:
            height = int(width / PICTURE_RATIO)
        if not width and height:
            width = int(height * PICTURE_RATIO)

        print ""
        print "##############"
        print "width", width
        print "height", height

        options = {
            'size': (width, height),
            'crop': crop,
            'upscale': upscale,
        }
        return options

    def get_link(self):
        if self.link_url:
            return self.link_url
        if self.link_page:
            return self.link_page.get_absolute_url(language=self.language)
        return False

    def clean(self):
        # there can be only one link type
        if self.link_url and self.link_page:
            raise ValidationError(
                ugettext('You have defined an external and internal link. '
                    'Only one option is allowed.')
            )

        # you shall only set one image kind
        if not self.picture and not self.external_picture:
            raise ValidationError('You need to add either an image or '
                'an external link to an image.')

        # certain cropping options do not work together, the following
        # list defines the disallowed options used in the ``clean`` method
        invalid_option_pairs = [
            ('use_automatic_scaling', 'use_no_cropping'),
            ('use_automatic_scaling', 'use_thumbnail'),
            ('use_no_cropping', 'use_crop'),
            ('use_no_cropping', 'use_upscale'),
            ('use_no_cropping', 'use_thumbnail'),
            ('use_thumbnail', 'use_crop'),
            ('use_thumbnail', 'use_upscale'),
        ]
        # invalid_option_pairs
        invalid_option_pair = None

        for pair in invalid_option_pairs:
            if getattr(self, pair[0]) and getattr(self, pair[1]):
                invalid_option_pair = pair
                break

        if invalid_option_pair:
            field_1 = self._meta.get_field(invalid_option_pair[0])
            field_2 = self._meta.get_field(invalid_option_pair[1])
            message = ugettext('The cropping selection is not valid. '
                'You cannot combine "{field_a}" with "{field_b}".'.format(
                    field_a = field_1.verbose_name,
                    field_b = field_2.verbose_name
                )
            )
            raise ValidationError(message)
