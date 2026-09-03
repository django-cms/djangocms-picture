from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FinderPictureConfig(AppConfig):
    name = "djangocms_picture.contrib.finder"
    label = "djangocms_picture_finder"
    verbose_name = _("djangocms-picture finder backend")
    default_auto_field = "django.db.models.AutoField"
