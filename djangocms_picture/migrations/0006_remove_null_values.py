# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_picture', '0005_reset_null_values'),
    ]

    operations = [
        migrations.AlterField(
            model_name='picture',
            name='link_url',
            field=models.URLField(default='', help_text='Wraps the image in a link to an external URL.', max_length=2040, verbose_name='External URL', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='picture',
            name='alignment',
            field=models.CharField(default='', choices=[('left', 'Align left'), ('right', 'Align right'), ('left', 'Align center')], max_length=255, blank=True, help_text='Aligns the image according to the selected option.', verbose_name='Alignment'),
            preserve_default=False,
        ),
    ]
