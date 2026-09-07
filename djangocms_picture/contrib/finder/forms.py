from collections.abc import Iterable
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from finder.forms.fields import FinderFileField
from finder.models.file import FileModel


class FinderImageChoiceField(FinderFileField):
    """Finder picker restricted to existing image inodes."""

    default_error_messages = {
        "missing": _("The selected finder image no longer exists."),
        "ambit": _("The selected finder image is not available in this image source."),
        "trashed": _("The selected finder image is in the trash."),
    }

    def __init__(
        self,
        *,
        allowed_ambits: Iterable[str] = (),
        **kwargs: Any,
    ) -> None:
        self.allowed_ambits = frozenset(allowed_ambits)
        super().__init__(**kwargs)

    def clean(self, value: Any) -> Any:
        image_id = super().clean(value)
        if image_id is None:
            return None
        try:
            image = FileModel.objects.get_inode(id=image_id, is_folder=False, mime_types=["image/*"])
        except FileModel.DoesNotExist as error:
            raise ValidationError(self.error_messages["missing"], code="missing") from error
        if image.folder.is_trash:
            raise ValidationError(self.error_messages["trashed"], code="trashed")
        if self.allowed_ambits and image.folder.get_ambit().slug not in self.allowed_ambits:
            raise ValidationError(self.error_messages["ambit"], code="ambit")
        return image_id
