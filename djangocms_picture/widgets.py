import json
from dataclasses import asdict
from typing import Any, Mapping, Sequence

from django import forms

from .backends.base import BasePictureBackend


class BackendImageWidget(forms.MultiWidget):
    """Render a backend selector and one named picker per backend."""

    template_name = "djangocms_picture/widgets/backend_image.html"

    def __init__(
        self,
        backends: Sequence[BasePictureBackend],
        widgets: Mapping[str, forms.Widget],
        attrs: Mapping[str, Any] | None = None,
    ) -> None:
        self.backends = tuple(backends)
        choices = [(backend.alias, backend.label) for backend in self.backends]
        backend_config = {
            backend.alias: {
                "configurationFields": sorted(backend.configuration_fields),
                "capabilities": asdict(backend.capabilities),
            }
            for backend in self.backends
        }
        selector = forms.Select(
            choices=choices,
            attrs={
                "data-picture-backend-selector": "",
                "data-picture-backends": json.dumps(backend_config),
            },
        )
        named_widgets: dict[str, forms.Widget] = {"backend": selector}
        for backend in self.backends:
            widget = widgets[backend.alias]
            widget.attrs["data-picture-backend-input"] = backend.alias
            named_widgets[backend.alias] = widget
        super().__init__(named_widgets, attrs)

    class Media:
        css = {"all": ("djangocms_picture/css/backend-image-widget.css",)}
        js = ("djangocms_picture/js/backend-image-widget.js",)

    def decompress(self, value: Any) -> list[Any]:
        from .fields import BackendSelection

        values: list[Any] = [None] * len(self.widgets)
        if not isinstance(value, BackendSelection):
            return values

        values[0] = value.backend
        try:
            index = next(
                index
                for index, backend in enumerate(self.backends, start=1)
                if backend.alias == value.backend
            )
        except StopIteration:
            return values
        values[index] = value.value
        return values

    def get_context(
        self,
        name: str,
        value: Any,
        attrs: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        context = forms.Widget.get_context(self, name, value, attrs)
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = True
        values = value if isinstance(value, (list, tuple)) else self.decompress(value)
        suffixes = ("backend", *(backend.alias for backend in self.backends))
        base_id = context["widget"]["attrs"].get("id")
        selected_alias = values[0] if values else None
        selected_alias = selected_alias or self.backends[0].alias

        subwidgets: list[dict[str, Any]] = []
        for index, (suffix, widget_name, widget) in enumerate(
            zip(suffixes, self.widgets_names, self.widgets)
        ):
            widget_attrs = context["widget"]["attrs"].copy()
            if base_id:
                widget_attrs["id"] = f"{base_id}_{suffix}"
            widget_value = values[index] if index < len(values) else None
            subwidgets.append(
                {
                    "backend_alias": None if index == 0 else suffix,
                    "backend_active": index == 0 or suffix == selected_alias,
                    "selector_hidden": index == 0 and len(self.backends) == 1,
                    "rendered": widget.render(
                        f"{name}{widget_name}",
                        widget_value,
                        attrs=widget_attrs,
                    ),
                }
            )
        context["widget"]["subwidgets"] = subwidgets
        return context
