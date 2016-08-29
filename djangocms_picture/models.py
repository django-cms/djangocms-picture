# -*- coding: utf-8 -*-
"""
Enables the user to add a "Picture" plugin that displays an image
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
from filer.fields.file import FilerFileField


# add setting for image alignment, renders a class or inline styles
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
        verbose_name=_('Picture'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    width = models.IntegerField(
        verbose_name=_('Width'),
        blank=True,
        null=True,
        help_text=_('The image width as number in pixel. '
            'Example: "720" and not "720px".'),
    )
    height = models.IntegerField(
        verbose_name=_('Height'),
        blank=True,
        null=True,
        help_text=_('The image height as number in pixel. '
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
        help_text=_('Usually used to display figurative or copyright information.')
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
        help_text=_('Wrapps a link around the image '
            'leading to an external url.'),
    )
    link_page = PageField(
        verbose_name=_('Internal URL'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text=_('Wraps a link around the image '
            'leading to an internal (page) url.'),
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
        help_text=_('Uses the placeholder size to automatically calculate the size.'),
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

    def __str__(self):
        if self.picture and self.picture.label:
            return self.picture.label
        return str(self.link_url or self.pk)

    def clean(self):
        if self.link_url and self.link_page:
            raise ValidationError(
                ugettext('You have defined an external and internal link. '
                    'Only one option is allowed.')
            )
        if (self.use_automatic_scaling and self.use_no_cropping or
            self.use_automatic_scaling and self.use_crop or
            self.use_automatic_scaling and self.use_upscale or
            self.use_automatic_scaling and self.use_thumbnail or
            self.use_no_cropping and self.use_crop or
            self.use_no_cropping and self.use_upscale or
            self.use_no_cropping and self.use_thumbnail or
            self.use_thumbnail and self.use_crop or
            self.use_thumbnail and self.use_upscale):
                # TODO add additional info about the error
                raise ValidationError(
                    ugettext('The cropping selection is not valid. '
                        'You cannot combine certain options.')
                )
