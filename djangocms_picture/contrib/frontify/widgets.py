import json
from collections.abc import Mapping
from typing import Any

from django import forms


class FrontifyPickerWidget(forms.Textarea):
    template_name = "djangocms_picture/widgets/frontify.html"

    def __init__(
        self,
        *,
        domain: str,
        client_id: str,
        finder_script_url: str,
        attrs: Mapping[str, Any] | None = None,
    ) -> None:
        self.domain = domain
        self.client_id = client_id
        self.finder_script_url = finder_script_url
        super().__init__(attrs={"hidden": True, **(attrs or {})})

    @property
    def media(self) -> forms.Media:
        return forms.Media(
            css={"all": ("djangocms_picture/css/frontify-picker.css",)},
            js=(
                self.finder_script_url,
                "djangocms_picture/js/frontify-picker.js",
            ),
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
        context["widget"].update(
            {
                "domain": self.domain,
                "client_id": self.client_id,
                "preview_url": payload.get("processing_url") or payload.get("previewUrl") or "",
                "label": payload.get("label") or payload.get("title") or payload.get("name") or "",
            }
        )
        return context
