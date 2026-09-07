from typing import Any

from django.db import migrations


def migrate_references(apps: Any, schema_editor: Any) -> None:
    Picture = apps.get_model("djangocms_picture", "Picture")
    Reference = apps.get_model("djangocms_picture_frontify", "FrontifyPictureReference")
    for extension in Reference.objects.iterator(chunk_size=500):
        if extension.picture_plugin.backend != "frontify":
            continue
        snapshot = {
            **extension.snapshot,
            "revision": extension.revision,
            "disabled": extension.disabled,
            "refreshed_at": extension.refreshed_at.isoformat() if extension.refreshed_at else None,
        }
        Picture.objects.filter(pk=extension.picture_plugin_id).update(
            picture_content_type_id=None,
            picture_object_id=None,
            picture_config={
                "version": 1,
                "backend": "frontify",
                "id": extension.asset_id,
                "context": {"account": extension.account},
                "snapshot": snapshot,
            },
        )


def restore_references(apps: Any, schema_editor: Any) -> None:
    Picture = apps.get_model("djangocms_picture", "Picture")
    Reference = apps.get_model("djangocms_picture_frontify", "FrontifyPictureReference")
    for picture in Picture.objects.filter(backend="frontify").iterator(chunk_size=500):
        config = picture.picture_config if isinstance(picture.picture_config, dict) else {}
        snapshot = config.get("snapshot") or {}
        Reference.objects.update_or_create(
            picture_plugin_id=picture.pk,
            defaults={
                "asset_id": str(config.get("id") or ""),
                "account": str((config.get("context") or {}).get("account") or ""),
                "snapshot": snapshot,
                "revision": str(snapshot.get("revision") or ""),
                "refreshed_at": snapshot.get("refreshed_at"),
                "disabled": bool(snapshot.get("disabled", False)),
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_picture", "0015_generic_picture_source"),
        ("djangocms_picture_frontify", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_references, restore_references),
        migrations.DeleteModel(name="FrontifyPictureReference"),
    ]
