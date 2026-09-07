from typing import Any

from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from djangocms_picture.backends import get_backend

from .backend import UNSPLASH_COLORS, UnsplashPictureBackend


class UnsplashPickerView(TemplateView):
    template_name = "djangocms_picture/admin/unsplash_picker.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        backend = get_backend("unsplash")
        if not isinstance(backend, UnsplashPictureBackend):
            raise TypeError('The configured "unsplash" backend must be UnsplashPictureBackend.')
        context.update(
            {
                "title": _("Select an Unsplash image"),
                "is_popup": True,
                "field_id": self.request.GET.get("field_id", ""),
                "access_key": str(backend.options["access_key"]).strip(),
                "application_name": backend.application_name,
                "per_page": backend.per_page,
                "content_filter": backend.options.get("content_filter", "high"),
                "collections": ",".join(backend.collections),
                "selected_orientation": backend.options.get("orientation", ""),
                "selected_color": backend.options.get("color", ""),
                "selected_order": backend.options.get("order_by", "relevant"),
                "orientation_choices": (
                    ("", _("Any orientation")),
                    ("landscape", _("Landscape")),
                    ("portrait", _("Portrait")),
                    ("squarish", _("Square")),
                ),
                "color_choices": tuple(
                    (value, label)
                    for value, label in (
                        ("", _("Any colour")),
                        ("black_and_white", _("Black and white")),
                        ("black", _("Black")),
                        ("white", _("White")),
                        ("yellow", _("Yellow")),
                        ("orange", _("Orange")),
                        ("red", _("Red")),
                        ("purple", _("Purple")),
                        ("magenta", _("Magenta")),
                        ("green", _("Green")),
                        ("teal", _("Teal")),
                        ("blue", _("Blue")),
                    )
                    if value in UNSPLASH_COLORS
                ),
                "order_choices": (
                    ("relevant", _("Relevant")),
                    ("latest", _("Latest")),
                ),
            }
        )
        return context
