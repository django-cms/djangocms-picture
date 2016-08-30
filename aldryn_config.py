# -*- coding: utf-8 -*-
from aldryn_client import forms


class Form(forms.BaseForm):
    alignment = forms.CharField(
        'List of alignment types, default "left, center, right" (comma separated)',
        required=False,
    )

    def clean(self):
        data = super(Form, self).clean()

        def split_and_strip(string):
            return [item.strip() for item in string.split(',') if item]

        data['alignment'] = split_and_strip(data['alignment'])
        return data

    def to_settings(self, data, settings):
        # validate aldryn settings
        if data['alignment']:
            settings['DJANGOCMS_PICTURE_ALIGN'] = [(item, item) for item in data['settings']]
        return settings
