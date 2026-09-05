import copy
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from .backends import get_backend, get_backends
from .backends.base import BasePictureBackend
from .widgets import BackendImageWidget


@dataclass(frozen=True)
class BackendSelection:
    """A cleaned backend and the value returned by its picker."""

    backend: BasePictureBackend
    value: Any

    def serialize(self) -> dict[str, Any]:
        """Return the selection as JSON-compatible backend and value data."""

        return {
            "backend": self.backend.alias,
            "value": _serialize_selection_value(self.value),
        }

    @classmethod
    def deserialize(
        cls,
        data: Mapping[str, Any],
        *,
        request: HttpRequest | None = None,
    ) -> "BackendSelection":
        """Restore a serialized selection using its configured backend field."""

        if not isinstance(data, Mapping):
            raise TypeError("A backend selection must be a mapping.")
        try:
            alias = data["backend"]
            serialized_value = data["value"]
        except KeyError as error:
            raise ValueError(f"Missing backend selection key: {error.args[0]}") from error
        if not isinstance(alias, str) or not alias:
            raise ValueError("The backend selection backend must be a non-empty string.")

        backend = get_backend(alias)
        value = _deserialize_selection_value(serialized_value)
        cleaned_value = backend.form_field(required=False, request=request).clean(value)
        return cls(backend=backend, value=cleaned_value)


def _serialize_selection_value(value: Any) -> Any:
    if isinstance(value, Model):
        if value.pk is None:
            raise ValueError("A model value must be saved before it can be serialized.")
        meta = value._meta
        return {
            "model": f"{meta.app_label}.{meta.model_name}",
            "pk": _json_compatible(value.pk),
        }
    if isinstance(value, Mapping):
        return {str(key): _serialize_selection_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_selection_value(item) for item in value]
    return _json_compatible(value)


def _deserialize_selection_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        if set(value) == {"model", "pk"}:
            model_label = value["model"]
            if not isinstance(model_label, str):
                raise ValueError("A serialized model reference requires a model label string.")
            try:
                model = apps.get_model(model_label)
            except LookupError as error:
                raise ValueError(
                    f'Unknown model in backend selection: "{model_label}".'
                ) from error
            if model is None:
                raise ValueError(f'Unknown model in backend selection: "{model_label}".')
            return model._default_manager.get(pk=value["pk"])
        return {str(key): _deserialize_selection_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deserialize_selection_value(item) for item in value]
    return value


def _json_compatible(value: Any) -> Any:
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


class BackendImageField(forms.Field):
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

        self.backends_by_alias = {backend.alias: backend for backend in self.backends}
        self.selector_field = forms.ChoiceField(
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
            required=required,
            widget=widget,
            **kwargs,
        )

    def __deepcopy__(self, memo: dict[int, Any]) -> "BackendImageField":
        obj = super().__deepcopy__(memo)
        obj.backends_by_alias = self.backends_by_alias.copy()
        obj.selector_field = copy.deepcopy(self.selector_field, memo)
        obj.backend_fields = copy.deepcopy(self.backend_fields, memo)
        return obj

    def clean(self, value: Any) -> BackendSelection | None:
        if self.disabled:
            value = self.initial() if callable(self.initial) else self.initial

        if value in self.empty_values:
            if self.required:
                raise ValidationError(self.error_messages["required"], code="required")
            return None

        if not isinstance(value, BackendSelection):
            raise ValidationError(
                self.error_messages["invalid_backend"],
                code="invalid_backend",
            )

        try:
            alias = self.selector_field.clean(value.backend.alias)
        except ValidationError as error:
            raise ValidationError(
                self.error_messages["invalid_backend"],
                code="invalid_backend",
            ) from error

        backend = self.backends_by_alias.get(alias)
        if backend is None:
            raise ValidationError(
                self.error_messages["invalid_backend"],
                code="invalid_backend",
            )

        cleaned_value = self.backend_fields[alias].clean(value.value)
        if cleaned_value in self.empty_values:
            if self.required:
                raise ValidationError(self.error_messages["required"], code="required")
            return None
        selection = BackendSelection(backend=backend, value=cleaned_value)
        self.run_validators(selection)
        return selection

    def has_changed(self, initial: Any, data: Any) -> bool:
        if self.disabled:
            return False
        if not isinstance(data, BackendSelection):
            return initial not in self.empty_values or data not in self.empty_values
        if not isinstance(initial, BackendSelection):
            return True
        if initial.backend.alias != data.backend.alias:
            return True
        return self.backend_fields[data.backend.alias].has_changed(initial.value, data.value)
