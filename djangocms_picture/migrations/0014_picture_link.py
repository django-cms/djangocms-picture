from typing import Any

from django.db import migrations
from django.db.models import Q

import djangocms_picture.linking


def migrate_existing_links(apps: Any, schema_editor: Any) -> None:
    Picture = apps.get_model("djangocms_picture", "Picture")
    pictures = Picture.objects.filter(
        (Q(link_url__isnull=False) & ~Q(link_url="")) | Q(link_page_id__isnull=False)
    )
    batch: list[Any] = []
    for picture in pictures.iterator(chunk_size=500):
        if picture.link_url:
            picture.link = {"external_link": picture.link_url}
        elif picture.link_page_id:
            picture.link = {"internal_link": f"cms.page:{picture.link_page_id}"}
        batch.append(picture)
        if len(batch) == 500:
            Picture.objects.bulk_update(batch, ["link"])
            batch.clear()
    if batch:
        Picture.objects.bulk_update(batch, ["link"])


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_picture", "0013_picture_backend"),
    ]

    operations = [
        migrations.AddField(
            model_name="picture",
            name="link",
            field=djangocms_picture.linking.PictureLinkField(
                blank=True,
                default=dict,
                help_text="-",
                verbose_name="Link",
            ),
        ),
        migrations.RunPython(migrate_existing_links, migrations.RunPython.noop),
    ]
