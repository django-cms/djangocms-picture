from django.db import models
from finder.models.fields import FinderFileField


class FinderPictureReference(models.Model):
    picture_plugin = models.OneToOneField(
        "djangocms_picture.Picture",
        related_name="finder_reference",
        on_delete=models.CASCADE,
    )
    image = FinderFileField(
        accept_mime_types=["image/*"],
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    ambit = models.SlugField(blank=True)
    snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Finder picture reference"
        verbose_name_plural = "Finder picture references"
