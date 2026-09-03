from typing import Any

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from finder.forms.fields import FinderFileField
from finder.models.file import FileModel


class FinderImageChoiceField(FinderFileField):
    """Finder picker restricted to existing image inodes."""

    default_error_messages = {
        "missing": _("The selected finder image no longer exists."),
    }

    def clean(self, value: Any) -> Any:
        image_id = super().clean(value)
        if image_id is None:
            return None
        try:
            FileModel.objects.get_inode(id=image_id, is_folder=False, mime_types=["image/*"])
        except FileModel.DoesNotExist as error:
            raise ValidationError(self.error_messages["missing"], code="missing") from error
        return image_id
