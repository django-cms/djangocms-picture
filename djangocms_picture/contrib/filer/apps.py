from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FilerPictureConfig(AppConfig):
    name = "djangocms_picture.contrib.filer"
    label = "djangocms_picture_filer"
    verbose_name = _("djangocms-picture filer backend")
    default_auto_field = "django.db.models.AutoField"
