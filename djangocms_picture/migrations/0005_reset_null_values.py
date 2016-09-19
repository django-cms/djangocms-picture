# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def reset_null_values(apps, schema_editor):
    Picture = apps.get_model('djangocms_picture', 'Picture')
    plugins = Picture.objects.all()
    plugins.filter(link_url__isnull=True).update(link_url='')
    plugins.filter(alignment__isnull=True).update(alignment='')


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_picture', '0004_adapt_fields'),
    ]

    operations = [
        migrations.RunPython(reset_null_values),
    ]
