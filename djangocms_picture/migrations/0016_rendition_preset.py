import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_picture", "0015_generic_picture_source"),
    ]

    operations = [
        migrations.CreateModel(
            name="RenditionPreset",
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
                ("name", models.CharField(max_length=100, verbose_name="Name")),
                (
                    "slug",
                    models.SlugField(
                        help_text="Stable identifier for this rendition preset.",
                        max_length=100,
                        unique=True,
                        verbose_name="Slug",
                    ),
                ),
                ("width", models.PositiveIntegerField(verbose_name="Width")),
                ("height", models.PositiveIntegerField(verbose_name="Height")),
                ("crop", models.BooleanField(default=False, verbose_name="Crop")),
                ("upscale", models.BooleanField(default=False, verbose_name="Upscale")),
            ],
            options={
                "verbose_name": "Rendition preset",
                "verbose_name_plural": "Rendition presets",
                "ordering": ("width", "height", "name"),
            },
        ),
        migrations.AddField(
            model_name="picture",
            name="rendition_preset",
            field=models.ForeignKey(
                blank=True,
                help_text="Overrides width, height, crop, and upscale for non-filer image backends.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="djangocms_picture.renditionpreset",
                verbose_name="Rendition preset",
            ),
        ),
    ]
