# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import cms.models.pluginmodel


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Picture',
            fields=[
                ('image', models.ImageField(upload_to=cms.models.pluginmodel.get_plugin_media_path, verbose_name='image')),
                ('url', models.CharField(help_text='If present, clicking on image will take user to link.', max_length=255, null=True, verbose_name='link', blank=True)),
                ('alt', models.CharField(help_text='Specifies an alternate text for an image, if the imagecannot be displayed.<br />Is also used by search enginesto classify the image.', max_length=255, null=True, verbose_name='alternate text', blank=True)),
                ('longdesc', models.CharField(help_text='When user hovers above picture, this text will appear in a popup.', max_length=255, null=True, verbose_name='long description', blank=True)),
                ('float', models.CharField(choices=[(b'left', 'left'), (b'right', 'right'), (b'center', 'center')], max_length=10, blank=True, help_text='Move image left, right or center.', null=True, verbose_name='side')),
                ('cmsplugin_ptr', models.OneToOneField(auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('page_link', models.ForeignKey(blank=True, to='cms.Page', help_text='If present, clicking on image will take user to specified page.', null=True, verbose_name='page')),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
    ]
