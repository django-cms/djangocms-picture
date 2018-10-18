# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_picture', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='picture',
            name='height',
            field=models.IntegerField(help_text='Pixel', null=True, verbose_name='height', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='picture',
            name='width',
            field=models.IntegerField(help_text='Pixel', null=True, verbose_name='width', blank=True),
            preserve_default=True,
        ),
    ]
