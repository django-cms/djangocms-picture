from typing import Any

from django.db import migrations


def migrate_references(apps: Any, schema_editor: Any) -> None:
    Picture = apps.get_model("djangocms_picture", "Picture")
    Reference = apps.get_model("djangocms_picture_finder", "FinderPictureReference")
    ContentType = apps.get_model("contenttypes", "ContentType")

    for extension in Reference.objects.iterator(chunk_size=500):
        picture = extension.picture_plugin
        image = extension.image
        if picture.backend != "finder" or image is None:
            continue
        content_type, _created = ContentType.objects.get_or_create(
            app_label=image._meta.app_label,
            model=image._meta.model_name,
        )
        previous_config = picture.picture_config if isinstance(picture.picture_config, dict) else {}
        previous_context = previous_config.get("context") or {}
        config = {
            "version": 1,
            "backend": "finder",
            "id": str(image.pk),
            "context": {
                "ambit": extension.ambit,
                **(
                    {"legacy_filer_id": previous_context["legacy_filer_id"]}
                    if previous_context.get("legacy_filer_id")
                    else {}
                ),
            },
            "snapshot": extension.snapshot,
        }
        Picture.objects.filter(pk=picture.pk).update(
            picture_content_type_id=content_type.pk,
            picture_object_id=str(image.pk),
            picture_config=config,
        )


def restore_references(apps: Any, schema_editor: Any) -> None:
    Picture = apps.get_model("djangocms_picture", "Picture")
    Reference = apps.get_model("djangocms_picture_finder", "FinderPictureReference")
    for picture in Picture.objects.filter(backend="finder").exclude(
        picture_object_id__isnull=True
    ).iterator(chunk_size=500):
        config = picture.picture_config if isinstance(picture.picture_config, dict) else {}
        Reference.objects.update_or_create(
            picture_plugin_id=picture.pk,
            defaults={
                "image_id": picture.picture_object_id,
                "ambit": (config.get("context") or {}).get("ambit", ""),
                "snapshot": config.get("snapshot") or {},
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_picture", "0015_generic_picture_source"),
        ("djangocms_picture_finder", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_references, restore_references),
        migrations.DeleteModel(name="FinderPictureReference"),
    ]
