from django.db import models


class UnsplashPictureReference(models.Model):
    picture_plugin = models.OneToOneField(
        "djangocms_picture.Picture",
        related_name="unsplash_reference",
        on_delete=models.CASCADE,
    )
    asset_id = models.CharField(max_length=255)
    snapshot = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Unsplash picture reference"
        verbose_name_plural = "Unsplash picture references"
