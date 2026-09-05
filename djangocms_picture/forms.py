from typing import Any

from django import forms
from django.conf import settings
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from .backends import BasePictureBackend, get_backend_for_instance, get_backends
from .fields import BackendImageField, BackendSelection
from .models import Picture, get_templates


class PictureForm(forms.ModelForm):
    """Select an image and expose only options supported by its backend."""

    # Django admin must see this as a declared field when it derives a plugin
    # form. __init__ replaces it with the request-aware composite field.
    image_source = forms.Field(label=_("Image source"))

    class Meta:
        model = Picture
        fields = "__all__"
        exclude = ("backend", "picture", "external_picture")
        widgets = {
            "caption_text": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(
        self,
        *args: Any,
        request: HttpRequest | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.request = request
        self.backends = get_backends()
        self.fields["image_source"] = BackendImageField(
            backends=self.backends,
            request=request,
            label=_("Image source"),
        )

        template_field = self.fields["template"]
        template_field.choices = get_templates()
        if len(template_field.choices) == 1:
            template_field.widget = forms.HiddenInput()
            self.initial.setdefault("template", template_field.choices[0][0])

        selected_backend = self._get_selected_backend()
        if not self.is_bound and "image_source" not in self.initial:
            value = None
            if self.instance:
                value = selected_backend.get_form_value(self.instance)
            self.initial["image_source"] = BackendSelection(
                backend=selected_backend,
                value=value,
            )
        self._configure_backend_fields(selected_backend)

    def _get_selected_backend(self) -> BasePictureBackend:
        if self.is_bound:
            alias = self.data.get(f'{self.add_prefix("image_source")}_backend')
        elif isinstance(self.initial.get("image_source"), BackendSelection):
            alias = self.initial["image_source"].backend.alias
        elif self.instance and self.instance.pk:
            alias = get_backend_for_instance(self.instance).alias
        else:
            model_default = Picture._meta.get_field("backend").default
            instance_backend = self.instance.backend
            alias = None
            if instance_backend != model_default:
                alias = instance_backend
            alias = alias or getattr(settings, "DJANGOCMS_PICTURE_DEFAULT_BACKEND", model_default)

        for backend in self.backends:
            if backend.alias == alias:
                return backend
        # Choice validation reports an invalid alias. A deterministic fallback
        # keeps the rest of the form usable while showing the field error.
        return self.backends[0]

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
        selection = cleaned_data.get("image_source")
        if isinstance(selection, BackendSelection):
            self._apply_selection(self.instance, selection)
        return cleaned_data

    @staticmethod
    def _apply_selection(instance: Picture, selection: BackendSelection) -> BasePictureBackend:
        backend = selection.backend
        instance.backend = backend.alias

        # external_picture historically overrides all other sources. Clear it
        # when leaving the URL backend, while retaining filer data when URL is
        # selected so existing rollback behavior remains available.
        if backend.alias != "url":
            instance.external_picture = None
        backend.set_form_value(instance, selection.value, commit=False)
        return backend

    def save(self, commit: bool = True) -> Picture:
        instance = super().save(commit=False)
        selection: BackendSelection = self.cleaned_data["image_source"]
        self._apply_selection(instance, selection)

        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def _save_m2m(self) -> None:
        """Persist backend-owned references after the plugin has a primary key."""

        super()._save_m2m()
        selection: BackendSelection = self.cleaned_data["image_source"]
        backend = selection.backend
        backend.set_form_value(self.instance, selection.value, commit=True)
