import json
from collections.abc import Mapping
from typing import Any

from django import forms


class UnsplashPickerWidget(forms.Textarea):
    template_name = "djangocms_picture/widgets/unsplash.html"

    def __init__(
        self,
        *,
        picker_url: str,
        application_name: str,
        attrs: Mapping[str, Any] | None = None,
    ) -> None:
        self.picker_url = picker_url
        self.application_name = application_name
        super().__init__(attrs={"hidden": True, **(attrs or {})})

    @property
    def media(self) -> forms.Media:
        return forms.Media(
            css={"all": ("djangocms_picture/css/unsplash-picker.css",)},
            js=("djangocms_picture/js/unsplash-picker.js",),
        )

    def format_value(self, value: Any) -> str:
        if isinstance(value, Mapping):
            return json.dumps(value)
        return super().format_value(value)

    def get_context(
        self,
        name: str,
        value: Any,
        attrs: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        payload = value
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        if not isinstance(payload, Mapping):
            payload = {}
        attribution = payload.get("attribution")
        if not isinstance(attribution, Mapping):
            attribution = {}
        context["widget"].update(
            {
                "picker_url": self.picker_url,
                "application_name": self.application_name,
                "preview_url": payload.get("preview_url") or "",
                "label": payload.get("label") or "",
                "photographer_name": attribution.get("creator_name") or "",
                "photographer_url": attribution.get("creator_url") or "",
                "photo_url": attribution.get("provider_url") or "",
            }
        )
        return context
