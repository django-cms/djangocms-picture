import django.db.models.deletion
import finder.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("djangocms_picture", "0013_picture_backend"),
        ("finder", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FinderPictureReference",
            fields=[
                (
                    "id",
                    models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("ambit", models.SlugField(blank=True)),
                ("snapshot", models.JSONField(blank=True, default=dict)),
                (
                    "image",
                    finder.models.fields.FinderFileField(
                        accept_mime_types=["image/*"],
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                    ),
                ),
                (
                    "picture_plugin",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="finder_reference",
                        to="djangocms_picture.picture",
                    ),
                ),
            ],
            options={
                "verbose_name": "Finder picture reference",
                "verbose_name_plural": "Finder picture references",
            },
        ),
    ]
