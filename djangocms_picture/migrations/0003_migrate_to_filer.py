# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import filer.fields.image
from filer.utils.loader import load_model


def migrate_to_filer(apps, schema_editor):
    # Because filer is polymorphic, Djangos migration can't handle
    Image = load_model(settings.FILER_IMAGE_MODEL)
    Picture = apps.get_model('djangocms_picture', 'Picture')
    plugins = Picture.objects.all()

    for plugin in plugins:
        if plugin.image:
            picture = Image.objects.get_or_create(
                file=plugin.image.file,
                defaults={
                    'name': plugin.image.name,
                    'default_alt_text': plugin.alt,
                    'default_caption': plugin.longdesc
                }
            )[0]
            plugins.filter(pk=plugin.pk).update(picture=picture)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.FILER_IMAGE_MODEL),
        ('filer', '0006_auto_20160623_1627'),
        ('djangocms_picture', '0002_auto_20151018_1927'),
    ]

    operations = [
        migrations.AddField(
            model_name='picture',
            name='picture',
            field=filer.fields.image.FilerImageField(related_name='+', on_delete=django.db.models.deletion.SET_NULL,
                                                     verbose_name='Picture', blank=True, to=settings.FILER_IMAGE_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='picture',
            name='cmsplugin_ptr',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, parent_link=True, related_name='djangocms_picture_picture', auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin'),
        ),
        migrations.RunPython(migrate_to_filer),
        migrations.RemoveField(
            model_name='picture',
            name='image',
        ),
        migrations.RemoveField(
            model_name='picture',
            name='alt',
        ),
        migrations.RemoveField(
            model_name='picture',
            name='longdesc',
        ),
    ]
