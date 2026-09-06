from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("djangocms_picture", "0013_picture_backend"),
    ]

    operations = [
        migrations.CreateModel(
            name="FrontifyPictureReference",
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
                ("account", models.CharField(blank=True, max_length=100)),
                ("snapshot", models.JSONField(default=dict)),
                ("revision", models.CharField(blank=True, max_length=255)),
                ("refreshed_at", models.DateTimeField(blank=True, null=True)),
                ("disabled", models.BooleanField(default=False)),
                (
                    "picture_plugin",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="frontify_reference",
                        to="djangocms_picture.picture",
                    ),
                ),
            ],
            options={
                "verbose_name": "Frontify picture reference",
                "verbose_name_plural": "Frontify picture references",
            },
        ),
    ]
