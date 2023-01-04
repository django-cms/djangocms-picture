from typing import Any, Dict, Iterable, List, Tuple
from easy_thumbnails.files import get_thumbnailer

from djangocms_picture.types import AlternativePictureData, SizesAttributeData

from .settings import RESPONSIVE_IMAGE_SIZES, RESPONSIVE_IMAGES_BREAKPOINTS


def get_srcset_sizes(picture_width: int) -> Iterable[int]:
    """
    Return version picture different sizes to generate according to RESPONSIVE_IMAGE_SIZES
    """
    return sorted(filter(
        lambda x: x <= picture_width,
        set(RESPONSIVE_IMAGE_SIZES + [picture_width]),
    ))


def generate_size_versions(base_picture, alt_picture_data: AlternativePictureData, image_format: str = None) -> List[Tuple[int, Dict[str, Any]]]:
    """
    Run easy thumbnail to generate resized versions for each `RESPONSIVE_IMAGE_SIZES` width of the given AlternativePictureData.
    Return list of tuples of (size, thumbnail)
    """
    thumbnailer = get_thumbnailer(alt_picture_data.picture)

    if image_format:
        # We suppose image format can do both (only used with WebP for now)
        thumbnailer.thumbnail_extension = image_format
        thumbnailer.thumbnail_transparency_extension = image_format

    picture_options = base_picture.get_size(alt_picture_data.picture.width, alt_picture_data.picture.height)
    picture_width = picture_options['size'][0]

    generate_sizes = get_srcset_sizes(picture_width)
    srcset_data = []
    for size in generate_sizes:
        srcset_data.append(
            (
                int(size),
                thumbnailer.get_thumbnail(
                    {'crop': picture_options['crop'], 'size': (size, size)}
                )
            )
        )
    return srcset_data


def get_srcset_attr(base_picture, alt_picture_data: AlternativePictureData, image_format: str = None) -> str:
    """
    Return "srcset" HTML attribute for the given AlternativePictureData
    """
    return ", ".join(
        f"{thumbnail.url} {size}w"
        for size, thumbnail in generate_size_versions(base_picture, alt_picture_data, image_format=image_format)
    )


def get_sizes_attr_data(base_picture, initial_size_id: str) -> List[SizesAttributeData]:
    """
    Return list of SizesAttributeData representing, for the given size, all parameters required to generate 
    `sizes` and `media` HTML attributes.
    For "small" return for large, medium, small. For "medium" return large, medium. For "large" return large.
    """
    alt_picture = base_picture.get_picture(initial_size_id)
    picture_options = base_picture.get_size(alt_picture.width, alt_picture.height)
    srcset_sizes = get_srcset_sizes(picture_width=picture_options['size'][0])

    sizes = []
    size_ids = list(RESPONSIVE_IMAGES_BREAKPOINTS.keys())
    breakpoints_after = size_ids[size_ids.index(initial_size_id):]
    for size_id in breakpoints_after:

        # If there is a picture for version greater than initial_size_id, stop as sizes will be managed in another source
        if sizes and base_picture.get_picture(size_id):
            break

        bp = RESPONSIVE_IMAGES_BREAKPOINTS[size_id]
        viewport_width = base_picture.get_picture_viewport_width(size_id)
        size_data = SizesAttributeData(
            breakpoint=bp,
            viewport_width=viewport_width,
            srcset_sizes=[size for size in srcset_sizes if size >= bp] if not viewport_width else [],
        )

        # skip params if they are the same as previous breakpoint
        if sizes and sizes[-1][1:] == size_data[1:]:
            continue

        sizes.append(size_data)

    sizes.reverse()
    return sizes


def get_sizes_attr(alt_picture_data: AlternativePictureData) -> str:
    """
    Return "sizes" HTML attribute for the given AlternativePictureData
    """

    has_many_versions = len(alt_picture_data.sizes_data) > 1
    min_bp = min(size_data.breakpoint for size_data in alt_picture_data.sizes_data)
    sizes = []
    for bp, vw, srcset_sizes in alt_picture_data.sizes_data:

        # we need min width condition on medium and large screen
        # but it's not necessary if there is only one alternative version
        need_min_width_condition = bp > min_bp and has_many_versions

        # If there is a used specified viewport width percent, simply use it
        if vw:
            if need_min_width_condition:
                sizes.append(f"(min-width: {bp}px) {vw}vw")
            else:
                sizes.append(f"{vw}vw")
        else:
            # Automatic case is to write a specific condition for each image size in px
            for index, size in enumerate(srcset_sizes):

                media_queries = ""
                if need_min_width_condition:
                    media_queries = f"(min-width: {bp}px)"

                # no max-width condition for last image size (original size)
                last_size = index == len(srcset_sizes) - 1
                if not last_size:
                    if media_queries:
                        media_queries += " and "
                    media_queries += f"(max-width: {size}px)"
                if media_queries:
                    media_queries = f"{media_queries} "
                sizes.append(f"{media_queries}{size}px")

    return ", ".join(sizes)


def get_media_attr(alt_picture_data: AlternativePictureData) -> str:
    """
    Return "media" HTML attribute for the given AlternativePictureData
    The condition is the smallest breakpoint of breakpoints concerned by the version
    """
    min_bp = min(size_data.breakpoint for size_data in alt_picture_data.sizes_data)
    return f"(min-width: {min_bp}px)" if min_bp else ""
