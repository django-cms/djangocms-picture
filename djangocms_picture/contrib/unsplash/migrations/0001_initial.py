import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("djangocms_picture", "0013_picture_backend"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnsplashPictureReference",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("asset_id", models.CharField(max_length=255)),
                ("snapshot", models.JSONField(default=dict)),
                (
                    "picture_plugin",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="unsplash_reference",
                        to="djangocms_picture.picture",
                    ),
                ),
            ],
            options={
                "verbose_name": "Unsplash picture reference",
                "verbose_name_plural": "Unsplash picture references",
            },
        ),
    ]
