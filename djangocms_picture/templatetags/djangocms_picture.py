from typing import Any

from django import template

from djangocms_picture.backends import BaseImageAsset, Rendition, RenditionSpec
from djangocms_picture.rendering import build_srcset

register = template.Library()


def _get_asset(value: Any) -> BaseImageAsset | None:
    return getattr(value, "image_asset", value)


@register.simple_tag
def picture_rendition(
    image: Any,
    width: int | str | None = None,
    height: int | str | None = None,
    crop: bool = False,
    upscale: bool = False,
) -> Rendition | None:
    asset = _get_asset(image)
    if not asset:
        return None
    return asset.get_rendition(
        RenditionSpec(
            width=int(width) if width else None,
            height=int(height) if height else None,
            crop=crop,
            upscale=upscale,
        )
    )


@register.simple_tag
def picture_srcset(
    image: Any,
    widths: str | list[int | str],
    crop: bool = False,
    upscale: bool = False,
) -> list[tuple[int, Rendition]]:
    asset = _get_asset(image)
    if isinstance(widths, str):
        widths = [part.strip() for part in widths.split(",") if part.strip()]
    return build_srcset(asset, widths=widths, crop=crop, upscale=upscale)
