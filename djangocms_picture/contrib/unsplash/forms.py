from collections.abc import Sequence
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .data import UnsplashPayloadError, normalize_unsplash_payload
from .widgets import UnsplashPickerWidget


class UnsplashImageChoiceField(forms.JSONField):
    default_error_messages = {
        "invalid_asset": _("Select a valid Unsplash image."),
    }

    def __init__(
        self,
        *,
        picker_url: str,
        application_name: str,
        allowed_image_hosts: Sequence[str] = ("images.unsplash.com",),
        **kwargs: Any,
    ) -> None:
        self.application_name = application_name
        self.allowed_image_hosts = tuple(allowed_image_hosts)
        kwargs.setdefault(
            "widget",
            UnsplashPickerWidget(
                picker_url=picker_url,
                application_name=application_name,
            ),
        )
        super().__init__(**kwargs)

    def clean(self, value: Any) -> dict[str, Any] | None:
        value = super().clean(value)
        if value in self.empty_values:
            return None
        try:
            return normalize_unsplash_payload(
                value,
                application_name=self.application_name,
                allowed_image_hosts=self.allowed_image_hosts,
            )
        except UnsplashPayloadError as error:
            raise ValidationError(
                self.error_messages["invalid_asset"],
                code="invalid_asset",
            ) from error
