# -*- coding: utf-8 -*-
from django import forms

from . import models


class PictureForm(forms.ModelForm):
    class Meta:
        model = models.Picture
        fields = '__all__'
        widgets = {
            'caption_text': forms.Textarea(attrs={'rows': 2}),
        }
