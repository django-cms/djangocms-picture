# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_picture', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='picture',
            name='style',
            field=models.CharField(max_length=255, help_text='Select an optional image style.', verbose_name='style', blank=True, null=True),
            preserve_default=True,
        ),
    ]
