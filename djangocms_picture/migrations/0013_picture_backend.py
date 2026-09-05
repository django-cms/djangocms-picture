from typing import Any

from django.db import migrations, models


def select_legacy_backends(apps: Any, schema_editor: Any) -> None:
    Picture = apps.get_model("djangocms_picture", "Picture")
    Picture.objects.exclude(external_picture__isnull=True).exclude(external_picture="").update(backend="url")


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_picture", "0012_alter_picture_cmsplugin_ptr"),
    ]

    operations = [
        migrations.AddField(
            model_name="picture",
            name="backend",
            field=models.CharField(default="filer", max_length=32, verbose_name="Image source"),
        ),
        migrations.RunPython(select_legacy_backends, migrations.RunPython.noop),
    ]
