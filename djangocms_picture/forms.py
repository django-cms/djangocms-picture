import json
from dataclasses import asdict
from typing import Any

from django import forms
from django.conf import settings
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from .backends import BasePictureBackend, get_backend, get_backend_choices, get_backend_for_instance, get_backends
from .models import Picture, get_templates


class PictureForm(forms.ModelForm):
    """Select an image and expose only options supported by its backend."""

    backend = forms.ChoiceField(label=_("Image source"))

    class Meta:
        model = Picture
        fields = "__all__"
        widgets = {
            "caption_text": forms.Textarea(attrs={"rows": 2}),
        }

    class Media:
        js = ("djangocms_picture/js/backend-form.js",)

    def __init__(
        self,
        *args: Any,
        request: HttpRequest | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.request = request
        self.backends = get_backends()

        template_field = self.fields["template"]
        template_field.choices = get_templates()
        if len(template_field.choices) == 1:
            template_field.widget = forms.HiddenInput()
            self.initial.setdefault("template", template_field.choices[0][0])

        backend_field = self.fields["backend"]
        backend_field.choices = get_backend_choices()
        backend_field.widget.attrs["data-picture-backend-selector"] = ""
        backend_field.widget.attrs["data-picture-backends"] = json.dumps(
            {
                backend.alias: {
                    "selectionField": backend.selection_field_name,
                    "configurationFields": sorted(backend.configuration_fields),
                    "capabilities": asdict(backend.capabilities),
                }
                for backend in self.backends
            }
        )

        selected_backend = self._get_selected_backend()
        self._configure_selection_fields(selected_backend)
        self._configure_backend_fields(selected_backend)

    def _get_selected_backend(self) -> BasePictureBackend:
        if self.is_bound:
            alias = self.data.get(self.add_prefix("backend"))
        elif self.instance and self.instance.pk:
            alias = get_backend_for_instance(self.instance).alias
            self.initial["backend"] = alias
        else:
            model_default = Picture._meta.get_field("backend").default
            instance_backend = self.instance.backend
            alias = self.initial.get("backend")
            if not alias and instance_backend != model_default:
                alias = instance_backend
            alias = alias or getattr(settings, "DJANGOCMS_PICTURE_DEFAULT_BACKEND", model_default)
            self.initial["backend"] = alias

        for backend in self.backends:
            if backend.alias == alias:
                return backend
        # Choice validation reports an invalid alias. A deterministic fallback
        # keeps the rest of the form usable while showing the field error.
        return get_backend("filer")

    def _configure_selection_fields(self, selected_backend: BasePictureBackend) -> None:
        for backend in self.backends:
            field = self.fields.get(backend.selection_field_name)
            if field is None:
                continue
            field.required = False
            field.disabled = backend.alias != selected_backend.alias
            field.widget.attrs["data-picture-backend-input"] = backend.alias

    def _configure_backend_fields(self, selected_backend: BasePictureBackend) -> None:
        configurable_fields = {
            field_name
            for backend in self.backends
            for field_name in backend.configuration_fields
        }
        for field_name in configurable_fields:
            field = self.fields.get(field_name)
            if field is None:
                continue
            field.disabled = not selected_backend.supports_configuration_field(field_name)
            field.widget.attrs["data-picture-backend-option"] = field_name

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        alias = cleaned_data.get("backend")
        if not alias:
            return cleaned_data

        backend = next((item for item in self.backends if item.alias == alias), None)
        if backend is None:
            return cleaned_data

        field_name = backend.selection_field_name
        if field_name not in self.fields:
            self.add_error("backend", _("The selected image source does not provide a picker."))
        elif not cleaned_data.get(field_name):
            self.add_error(field_name, _("Select an image from this source."))
        return cleaned_data

    def save(self, commit: bool = True) -> Picture:
        instance = super().save(commit=False)
        backend = get_backend(self.cleaned_data["backend"])

        # external_picture historically overrides all other sources. Clear it
        # when leaving the URL backend, while retaining filer data when URL is
        # selected so existing rollback behavior remains available.
        if backend.alias != "url":
            instance.external_picture = None

        value = self.cleaned_data.get(backend.selection_field_name)
        backend.set_form_value(instance, value, commit=False)

        if commit:
            instance.save()
            backend.set_form_value(instance, value, commit=True)
            self.save_m2m()
        return instance


def _install_backend_form_fields() -> None:
    """Install non-model picker fields declared by optional contrib backends."""

    for backend in get_backends():
        if backend.selection_field_name not in PictureForm.base_fields:
            PictureForm.base_fields[backend.selection_field_name] = backend.form_field(required=False)


_install_backend_form_fields()
