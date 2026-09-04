from dataclasses import dataclass
from typing import Any, Iterable

from django import forms
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from .backends import get_backends
from .backends.base import BasePictureBackend
from .widgets import BackendImageWidget


@dataclass(frozen=True)
class BackendSelection:
    """A cleaned backend alias and the value returned by its picker."""

    backend: str
    value: Any


class BackendImageField(forms.MultiValueField):
    """Validate only the picker belonging to the selected image backend."""

    default_error_messages = {
        "invalid_backend": _("Select a valid image source."),
        "required": _("Select an image from this source."),
    }

    def __init__(
        self,
        *,
        backends: Iterable[BasePictureBackend] | None = None,
        request: HttpRequest | None = None,
        required: bool = True,
        widget: BackendImageWidget | None = None,
        **kwargs: Any,
    ) -> None:
        self.backends = tuple(backends if backends is not None else get_backends())
        aliases = [backend.alias for backend in self.backends]
        if not aliases:
            raise ValueError("BackendImageField requires at least one backend.")
        if len(aliases) != len(set(aliases)):
            raise ValueError("BackendImageField backend aliases must be unique.")

        selector = forms.ChoiceField(
            choices=[(backend.alias, backend.label) for backend in self.backends]
        )
        backend_fields = {
            backend.alias: backend.form_field(required=False, request=request)
            for backend in self.backends
        }
        if widget is None:
            widget = BackendImageWidget(
                self.backends,
                {alias: field.widget for alias, field in backend_fields.items()},
            )
        self.backend_fields = backend_fields
        kwargs.setdefault("label", _("Image source"))
        super().__init__(
            fields=(selector, *backend_fields.values()),
            require_all_fields=False,
            required=required,
            widget=widget,
            **kwargs,
        )

    @property
    def selector_field(self) -> forms.ChoiceField:
        return self.fields[0]

    def clean(self, value: Any) -> BackendSelection | None:
        if self.disabled:
            value = self.initial() if callable(self.initial) else self.initial
            value = self.widget.decompress(value)

        if not isinstance(value, (list, tuple)):
            value = []
        if not value or all(item in self.empty_values for item in value):
            if self.required:
                raise ValidationError(self.error_messages["required"], code="required")
            return None

        raw_alias = value[0] if value else None
        try:
            alias = self.selector_field.clean(raw_alias)
        except ValidationError as error:
            raise ValidationError(
                self.error_messages["invalid_backend"],
                code="invalid_backend",
            ) from error

        try:
            index = next(
                index
                for index, backend in enumerate(self.backends, start=1)
                if backend.alias == alias
            )
        except StopIteration as error:
            raise ValidationError(
                self.error_messages["invalid_backend"],
                code="invalid_backend",
            ) from error

        raw_value = value[index] if index < len(value) else None
        cleaned_value = self.fields[index].clean(raw_value)
        if cleaned_value in self.empty_values:
            if self.required:
                raise ValidationError(self.error_messages["required"], code="required")
            return None
        return BackendSelection(backend=alias, value=cleaned_value)

    def compress(self, data_list: list[Any]) -> BackendSelection | None:
        if not data_list:
            return None
        alias = data_list[0]
        try:
            index = next(
                index
                for index, backend in enumerate(self.backends, start=1)
                if backend.alias == alias
            )
        except StopIteration:
            return None
        value = data_list[index] if index < len(data_list) else None
        return BackendSelection(backend=alias, value=value)
