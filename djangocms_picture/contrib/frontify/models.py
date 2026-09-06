from django.db import models


class FrontifyPictureReference(models.Model):
    picture_plugin = models.OneToOneField(
        "djangocms_picture.Picture",
        related_name="frontify_reference",
        on_delete=models.CASCADE,
    )
    asset_id = models.CharField(max_length=255)
    account = models.CharField(max_length=100, blank=True)
    snapshot = models.JSONField(default=dict)
    revision = models.CharField(max_length=255, blank=True)
    refreshed_at = models.DateTimeField(blank=True, null=True)
    disabled = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Frontify picture reference"
        verbose_name_plural = "Frontify picture references"
