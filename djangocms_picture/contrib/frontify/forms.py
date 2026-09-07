from collections.abc import Sequence
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .data import FrontifyPayloadError, normalize_frontify_payload
from .widgets import FrontifyPickerWidget


class FrontifyImageChoiceField(forms.JSONField):
    default_error_messages = {
        "invalid_asset": _("Select a valid Frontify image."),
    }

    def __init__(
        self,
        *,
        domain: str,
        client_id: str,
        finder_script_url: str,
        allowed_hosts: Sequence[str] = (),
        alt_text_field: str = "alt-tag_{language_code}",
        allow_expiring_urls: bool = False,
        **kwargs: Any,
    ) -> None:
        self.allowed_hosts = tuple(allowed_hosts)
        self.alt_text_field = alt_text_field
        self.allow_expiring_urls = allow_expiring_urls
        kwargs.setdefault(
            "widget",
            FrontifyPickerWidget(
                domain=domain,
                client_id=client_id,
                finder_script_url=finder_script_url,
            ),
        )
        super().__init__(**kwargs)

    def clean(self, value: Any) -> dict[str, Any] | None:
        value = super().clean(value)
        if value in self.empty_values:
            return None
        try:
            snapshot = normalize_frontify_payload(
                value,
                allowed_hosts=self.allowed_hosts,
                alt_text_field=self.alt_text_field,
            )
            if snapshot.get("expires_at") and not self.allow_expiring_urls:
                raise FrontifyPayloadError("Expiring Frontify URLs are not enabled.")
            return snapshot
        except FrontifyPayloadError as error:
            raise ValidationError(
                self.error_messages["invalid_asset"],
                code="invalid_asset",
            ) from error
