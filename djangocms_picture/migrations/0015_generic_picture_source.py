from typing import Any

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


def _reference(backend: str, identifier: Any, *, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "version": 1,
        "backend": backend,
        "id": str(identifier),
        "context": {},
        "snapshot": snapshot or {},
    }


def migrate_legacy_sources(apps: Any, schema_editor: Any) -> None:
    Picture = apps.get_model("djangocms_picture", "Picture")
    ContentType = apps.get_model("contenttypes", "ContentType")
    app_label, model_name = settings.FILER_IMAGE_MODEL.split(".", 1)
    filer_content_type, _created = ContentType.objects.get_or_create(
        app_label=app_label,
        model=model_name.lower(),
    )

    batch: list[Any] = []
    pictures = Picture.objects.select_related("picture").exclude(
        Q(picture__isnull=True) & (Q(external_picture__isnull=True) | Q(external_picture=""))
    )
    for picture in pictures.iterator(chunk_size=500):
        if picture.external_picture:
            image = picture.picture
            snapshot = {
                "width": getattr(image, "_width", None),
                "height": getattr(image, "_height", None),
                "alt_text": getattr(image, "default_alt_text", "") or "",
            }
            picture.backend = "url"
            picture.picture_content_type_id = None
            picture.picture_object_id = None
            picture.picture_config = _reference("url", picture.external_picture, snapshot=snapshot)
        elif picture.picture_id:
            if picture.backend in {"", "filer"}:
                picture.backend = "filer"
                picture.picture_content_type_id = filer_content_type.pk
                picture.picture_object_id = str(picture.picture_id)
                picture.picture_config = _reference("filer", picture.picture_id)
            elif picture.backend == "finder":
                picture.picture_config = {
                    **_reference("finder", picture.picture_id),
                    "context": {"legacy_filer_id": str(picture.picture_id)},
                }
            else:
                continue
        else:
            continue
        batch.append(picture)
        if len(batch) == 500:
            Picture.objects.bulk_update(
                batch,
                ("backend", "picture_content_type", "picture_object_id", "picture_config"),
            )
            batch.clear()
    if batch:
        Picture.objects.bulk_update(
            batch,
            ("backend", "picture_content_type", "picture_object_id", "picture_config"),
        )


def restore_legacy_sources(apps: Any, schema_editor: Any) -> None:
    Picture = apps.get_model("djangocms_picture", "Picture")
    batch: list[Any] = []
    for picture in Picture.objects.exclude(picture_config={}).iterator(chunk_size=500):
        config = picture.picture_config
        if not isinstance(config, dict):
            continue
        if config.get("backend") == "url":
            picture.external_picture = str(config.get("id") or "") or None
        elif config.get("backend") == "filer":
            picture.picture_id = picture.picture_object_id
        else:
            continue
        batch.append(picture)
        if len(batch) == 500:
            Picture.objects.bulk_update(batch, ("picture", "external_picture"))
            batch.clear()
    if batch:
        Picture.objects.bulk_update(batch, ("picture", "external_picture"))


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("djangocms_picture", "0014_picture_link"),
    ]

    operations = [
        migrations.AddField(
            model_name="picture",
            name="picture_config",
            field=models.JSONField(blank=True, default=dict, verbose_name="Image source configuration"),
        ),
        migrations.AddField(
            model_name="picture",
            name="picture_content_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="contenttypes.contenttype",
                verbose_name="Image model",
            ),
        ),
        migrations.AddField(
            model_name="picture",
            name="picture_object_id",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="Image object ID"),
        ),
        migrations.RunPython(migrate_legacy_sources, restore_legacy_sources),
        migrations.RemoveField(model_name="picture", name="external_picture"),
        migrations.RemoveField(model_name="picture", name="picture"),
        migrations.AddIndex(
            model_name="picture",
            index=models.Index(
                fields=("picture_content_type", "picture_object_id"),
                name="dcp_picture_object_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="picture",
            constraint=models.CheckConstraint(
                condition=(
                    Q(picture_content_type__isnull=True, picture_object_id__isnull=True)
                    | Q(picture_content_type__isnull=False, picture_object_id__isnull=False)
                ),
                name="dcp_picture_object_pair",
            ),
        ),
    ]
