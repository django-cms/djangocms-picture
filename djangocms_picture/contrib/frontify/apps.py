from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FrontifyPictureConfig(AppConfig):
    name = "djangocms_picture.contrib.frontify"
    label = "djangocms_picture_frontify"
    verbose_name = _("djangocms-picture Frontify backend")
    default_auto_field = "django.db.models.AutoField"
