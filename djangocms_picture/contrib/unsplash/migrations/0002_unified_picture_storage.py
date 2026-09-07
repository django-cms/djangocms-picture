from typing import Any

from django.db import migrations


def migrate_references(apps: Any, schema_editor: Any) -> None:
    Picture = apps.get_model("djangocms_picture", "Picture")
    Reference = apps.get_model("djangocms_picture_unsplash", "UnsplashPictureReference")
    for extension in Reference.objects.iterator(chunk_size=500):
        if extension.picture_plugin.backend != "unsplash":
            continue
        Picture.objects.filter(pk=extension.picture_plugin_id).update(
            picture_content_type_id=None,
            picture_object_id=None,
            picture_config={
                "version": 1,
                "backend": "unsplash",
                "id": extension.asset_id,
                "context": {},
                "snapshot": extension.snapshot,
            },
        )


def restore_references(apps: Any, schema_editor: Any) -> None:
    Picture = apps.get_model("djangocms_picture", "Picture")
    Reference = apps.get_model("djangocms_picture_unsplash", "UnsplashPictureReference")
    for picture in Picture.objects.filter(backend="unsplash").iterator(chunk_size=500):
        config = picture.picture_config if isinstance(picture.picture_config, dict) else {}
        Reference.objects.update_or_create(
            picture_plugin_id=picture.pk,
            defaults={
                "asset_id": str(config.get("id") or ""),
                "snapshot": config.get("snapshot") or {},
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_picture", "0015_generic_picture_source"),
        ("djangocms_picture_unsplash", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_references, restore_references),
        migrations.DeleteModel(name="UnsplashPictureReference"),
    ]
