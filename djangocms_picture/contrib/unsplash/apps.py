from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UnsplashPictureConfig(AppConfig):
    name = "djangocms_picture.contrib.unsplash"
    label = "djangocms_picture_unsplash"
    verbose_name = _("djangocms-picture Unsplash backend")
    default_auto_field = "django.db.models.AutoField"
