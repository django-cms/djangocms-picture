from functools import partial

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import (
    ALTERNATIVE_FORMAT_WEBP_CHOICES, USE_RESPONSIVE_IMAGE_CHOICES, Picture,
)
from .settings import (
    RESPONSIVE_IMAGES_ALTERNATIVE_FORMAT_WEBP, RESPONSIVE_IMAGES_ENABLED,
)


def choices_with_explicit_default(choices, default_value):
    new_choices = []
    for key, label in choices:
        if key == 'inherit':
            default_value_str = default_value and _('Yes') or _('No')
            label = f"{label} [{default_value_str}]"
        new_choices.append((key, label))
    return new_choices


class PictureForm(forms.ModelForm):

    class Meta:
        model = Picture
        fields = '__all__'
        widgets = {
            'caption_text': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["use_responsive_image"].choices = choices_with_explicit_default(
            USE_RESPONSIVE_IMAGE_CHOICES, RESPONSIVE_IMAGES_ENABLED)
        self.fields["alternative_format_webp"].choices = choices_with_explicit_default(
            ALTERNATIVE_FORMAT_WEBP_CHOICES, RESPONSIVE_IMAGES_ALTERNATIVE_FORMAT_WEBP)
