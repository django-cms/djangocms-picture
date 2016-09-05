# -*- coding: utf-8 -*-
from aldryn_client import forms


class Form(forms.BaseForm):
    templates = forms.CharField(
        'List of additional templates (comma separated)',
        required=False,
    )
    alignment = forms.CharField(
        'List of alignment types, default "left, center, right" (comma separated)',
        required=False,
    )
    ratio = forms.NumberField(
        'The ratio used to calculate the missing width or height, default "1.618"',
        required=False,
    )
    nesting = forms.BooleanField(
        'Allow plugins to be nested inside the picture plugin.',
        required=False,
        default=False,
    )

    def clean(self):
        data = super(Form, self).clean()

        def split_and_strip(string):
            return [item.strip() for item in string.split(',') if item]

        data['templates'] = split_and_strip(data['templates'])
        data['alignment'] = split_and_strip(data['alignment'])
        return data

    def to_settings(self, data, settings):
        # validate aldryn settings
        if data['templates']:
            settings['DJANGOCMS_PICTURE_TEMPLATES'] = [(item, item) for item in data['templates']]
        if data['alignment']:
            settings['DJANGOCMS_PICTURE_ALIGN'] = [(item, item) for item in data['alignment']]
        if data['ratio']:
            settings['DJANGOCMS_PICTURE_RATIO'] = data['ratio']
        if data['nesting']:
            settings['DJANGOCMS_PICTURE_NESTING'] = data['nesting']
        return settings
