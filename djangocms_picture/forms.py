# -*- coding: utf-8 -*-
from django import forms

from .models import Picture


class PictureForm(forms.ModelForm):

    class Meta:
        model = Picture
        fields = '__all__'
        widgets = {
            'caption_text': forms.Textarea(attrs={'rows': 2}),
        }
