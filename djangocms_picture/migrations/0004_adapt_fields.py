# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import djangocms_attributes_field.fields
import cms.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_picture', '0003_migrate_to_filer'),
    ]

    operations = [
        migrations.AddField(
            model_name='picture',
            name='attributes',
            field=djangocms_attributes_field.fields.AttributesField(default=dict, verbose_name='Attributes', blank=True),
        ),
        migrations.AddField(
            model_name='picture',
            name='caption_text',
            field=models.TextField(help_text='Usually used to display figurative or copyright information.', verbose_name='Caption text', blank=True),
        ),
        migrations.AddField(
            model_name='picture',
            name='link_attributes',
            field=djangocms_attributes_field.fields.AttributesField(default=dict, verbose_name='Link attributes', blank=True),
        ),
        migrations.AddField(
            model_name='picture',
            name='link_target',
            field=models.CharField(blank=True, max_length=255, verbose_name='Link target', choices=[(b'_blank', 'Open in new window.'), (b'_self', 'Open in same window.'), (b'_parent', 'Delegate to parent.'), (b'_top', 'Delegate to top.')]),
        ),
        migrations.AddField(
            model_name='picture',
            name='use_automatic_scaling',
            field=models.BooleanField(default=True, help_text='Uses the placeholder size to automatically calculate the size.', verbose_name='Automatic scaling'),
        ),
        migrations.AddField(
            model_name='picture',
            name='use_crop',
            field=models.BooleanField(default=False, help_text='Crops the image according to the given thumbnail settings in the template.', verbose_name='Crop image'),
        ),
        migrations.AddField(
            model_name='picture',
            name='use_no_cropping',
            field=models.BooleanField(default=False, help_text='Outputs the raw image without cropping.', verbose_name='Use original image.'),
        ),
        migrations.AddField(
            model_name='picture',
            name='use_upscale',
            field=models.BooleanField(default=False, help_text='Upscales the image to the size of the thumbnail settings in the template.', verbose_name='Upscale image'),
        ),
        migrations.AddField(
            model_name='picture',
            name='use_thumbnail',
            field=models.ForeignKey(blank=True, to='filer.ThumbnailOption', help_text='Overrides width, height, crop and upscale with the provided preset.', null=True, verbose_name='Thumbnail options'),
        ),
        migrations.RenameField(
            model_name='picture',
            old_name='float',
            new_name='alignment',
        ),
        migrations.RenameField(
            model_name='picture',
            old_name='url',
            new_name='link_url',
        ),
        migrations.RenameField(
            model_name='picture',
            old_name='page_link',
            new_name='link_page',
        ),
        migrations.AlterField(
            model_name='picture',
            name='alignment',
            field=models.CharField(default='', choices=[(b'left', 'Align left'), (b'right', 'Align right'), (b'left', 'Align center')], max_length=255, blank=True, help_text='Aligns the image to the selected option.', verbose_name='Alignment'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='picture',
            name='height',
            field=models.IntegerField(help_text='The image height as number in pixel. Example: "720" and not "720px".', null=True, verbose_name='Height', blank=True),
        ),
        migrations.AlterField(
            model_name='picture',
            name='width',
            field=models.IntegerField(help_text='The image width as number in pixel. Example: "720" and not "720px".', null=True, verbose_name='Width', blank=True),
        ),
        migrations.AlterField(
            model_name='picture',
            name='link_page',
            field=cms.models.fields.PageField(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='cms.Page', help_text='Wraps a link around the image leading to an internal (page) url.', null=True, verbose_name='Internal URL'),
        ),
        migrations.AlterField(
            model_name='picture',
            name='link_url',
            field=models.URLField(default='', help_text='Wrapps a link around the image leading to an external url.', max_length=255, verbose_name='External URL', blank=True),
            preserve_default=False,
        ),
    ]
