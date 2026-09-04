from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DjangocmsPictureConfig(AppConfig):
    name = "djangocms_picture"
    verbose_name = _("django CMS Picture")
    default_auto_field = "django.db.models.AutoField"

    def ready(self) -> None:
        from . import checks  # noqa: F401
