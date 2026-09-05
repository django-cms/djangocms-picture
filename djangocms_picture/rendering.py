from collections.abc import Iterable

from .backends import BaseImageAsset, ImageInfo, Rendition, RenditionSpec


def calculate_size(
    image_info: ImageInfo | None,
    *,
    width: int | float | None = None,
    height: int | float | None = None,
    crop: bool = False,
    upscale: bool = False,
    picture_ratio: float = 1.618,
) -> RenditionSpec:
    """Normalize requested dimensions independently of an image backend."""

    if image_info:
        if crop:
            if not height and width:
                if image_info.width and image_info.height and image_info.width > image_info.height:
                    height = width / picture_ratio
                else:
                    height = width * picture_ratio
            elif not width and height:
                if image_info.width and image_info.height and image_info.width > image_info.height:
                    width = height * picture_ratio
                else:
                    width = height / picture_ratio

        width = width or image_info.width
        height = height or image_info.height

    return RenditionSpec(
        width=int(width) if width is not None else None,
        height=int(height) if height is not None else None,
        crop=crop,
        upscale=upscale,
    )


def build_srcset(
    asset: BaseImageAsset | None,
    *,
    widths: Iterable[int | str],
    width: int | None = None,
    height: int | None = None,
    crop: bool = False,
    upscale: bool = False,
) -> list[tuple[int, Rendition]]:
    if not asset or not asset.capabilities.responsive:
        return []
    source_width = width or asset.info.width
    if not source_width:
        return []

    renditions: list[tuple[int, Rendition]] = []
    rendered_widths: set[int] = set()
    for candidate_width in sorted(set(int(value) for value in widths)):
        if candidate_width >= source_width:
            continue
        spec = RenditionSpec(
            width=candidate_width,
            # Preserve the existing easy-thumbnails request shape. Backends
            # return the actual rendered dimensions in the Rendition object.
            height=candidate_width,
            crop=crop,
            upscale=upscale,
        )
        rendition = asset.get_rendition(spec)
        rendered_width = rendition.width or candidate_width
        if rendered_width not in rendered_widths:
            renditions.append((rendered_width, rendition))
            rendered_widths.add(rendered_width)
    return renditions
