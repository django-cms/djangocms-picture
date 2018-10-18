# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import cms.models.pluginmodel
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Picture',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, serialize=False, parent_link=True, auto_created=True, to='cms.CMSPlugin', primary_key=True)),
                ('image', models.ImageField(verbose_name='image', upload_to=cms.models.pluginmodel.get_plugin_media_path)),
                ('url', models.CharField(help_text='If present, clicking on image will take user to link.', blank=True, null=True, max_length=255, verbose_name='link')),
                ('alt', models.CharField(help_text='Specifies an alternate text for an image, if the imagecannot be displayed.<br />Is also used by search enginesto classify the image.', blank=True, null=True, max_length=255, verbose_name='alternate text')),
                ('longdesc', models.CharField(help_text='When user hovers above picture, this text will appear in a popup.', blank=True, null=True, max_length=255, verbose_name='long description')),
                ('float', models.CharField(help_text='Move image left, right or center.', blank=True, max_length=10, choices=[('left', 'left'), ('right', 'right'), ('center', 'center')], verbose_name='side', null=True)),
                ('page_link', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, help_text='If present, clicking on image will take user to specified page.', blank=True, verbose_name='page', to='cms.Page', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
    ]
