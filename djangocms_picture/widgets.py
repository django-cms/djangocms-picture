import copy
import json
from dataclasses import asdict
from typing import Any, Mapping, Sequence

from django import forms

from .backends.base import BasePictureBackend


class BackendImageWidget(forms.Widget):
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
        self.selector_widget = forms.Select(
            choices=choices,
            attrs={
                "data-picture-backend-selector": "",
                "data-picture-backends": json.dumps(backend_config),
            },
        )
        self.backend_widgets: dict[str, forms.Widget] = {}
        for backend in self.backends:
            widget = widgets[backend.alias]
            widget.attrs["data-picture-backend-input"] = backend.alias
            self.backend_widgets[backend.alias] = widget
        super().__init__(attrs)

    class Media:
        css = {"all": ("djangocms_picture/css/backend-image-widget.css",)}
        js = ("djangocms_picture/js/backend-image-widget.js",)

    @property
    def media(self) -> forms.Media:
        media = forms.Media(css=self.Media.css, js=self.Media.js)
        media += self.selector_widget.media
        for widget in self.backend_widgets.values():
            media += widget.media
        return media

    @property
    def needs_multipart_form(self) -> bool:
        return any(widget.needs_multipart_form for widget in self.backend_widgets.values())

    def __deepcopy__(self, memo: dict[int, Any]) -> "BackendImageWidget":
        obj = super().__deepcopy__(memo)
        obj.selector_widget = copy.deepcopy(self.selector_widget, memo)
        obj.backend_widgets = copy.deepcopy(self.backend_widgets, memo)
        return obj

    def value_from_datadict(
        self,
        data: Mapping[str, Any],
        files: Mapping[str, Any],
        name: str,
    ) -> Any:
        from .fields import BackendSelection

        alias = self.selector_widget.value_from_datadict(data, files, f"{name}_backend")
        backend = next((backend for backend in self.backends if backend.alias == alias), None)
        if backend is None:
            return alias
        value = self.backend_widgets[alias].value_from_datadict(
            data,
            files,
            f"{name}_{alias}",
        )
        return BackendSelection(backend=backend, value=value)

    def value_omitted_from_data(
        self,
        data: Mapping[str, Any],
        files: Mapping[str, Any],
        name: str,
    ) -> bool:
        return self.selector_widget.value_omitted_from_data(data, files, f"{name}_backend")

    def id_for_label(self, id_: str) -> str:
        return f"{id_}_backend" if id_ else ""

    def use_required_attribute(self, initial: Any) -> bool:
        return False

    def get_context(
        self,
        name: str,
        value: Any,
        attrs: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        from .fields import BackendSelection

        context = super().get_context(name, value, attrs)
        child_widgets = (self.selector_widget, *self.backend_widgets.values())
        if self.is_localized:
            for widget in child_widgets:
                widget.is_localized = True

        selection = value if isinstance(value, BackendSelection) else None
        suffixes = ("backend", *(backend.alias for backend in self.backends))
        base_id = context["widget"]["attrs"].get("id")
        selected_alias = selection.backend.alias if selection else self.backends[0].alias

        subwidgets: list[dict[str, Any]] = []
        for index, (suffix, widget) in enumerate(zip(suffixes, child_widgets)):
            widget_attrs = context["widget"]["attrs"].copy()
            if base_id:
                widget_attrs["id"] = f"{base_id}_{suffix}"
            if index == 0:
                widget_value = selected_alias
            elif suffix == selected_alias and selection:
                widget_value = selection.value
            else:
                widget_value = None
            subwidgets.append(
                {
                    "backend_alias": None if index == 0 else suffix,
                    "backend_active": index == 0 or suffix == selected_alias,
                    "selector_hidden": index == 0 and len(self.backends) == 1,
                    "rendered": widget.render(
                        f"{name}_{suffix}",
                        widget_value,
                        attrs=widget_attrs,
                    ),
                }
            )
        context["widget"]["subwidgets"] = subwidgets
        return context
