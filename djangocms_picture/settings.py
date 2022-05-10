from django.conf import settings
from django.utils.translation import gettext_lazy as _

TEMPLATES = getattr(settings, 'DJANGOCMS_PICTURE_TEMPLATES', [])

# enable nesting of plugins inside the picture plugin
PICTURE_NESTING = getattr(settings, 'DJANGOCMS_PICTURE_NESTING', False)

# use golden ration as default (https://en.wikipedia.org/wiki/Golden_ratio)
PICTURE_RATIO = getattr(settings, "DJANGOCMS_PICTURE_RATIO", 1.6180)

PICTURE_ALIGN = getattr(
    settings,
    "DJANGOCMS_PICTURE_ALIGN",
    (
        ("left", _("Align left")),
        ("right", _("Align right")),
        ("center", _("Align center")),
    ),
)

RESPONSIVE_IMAGES_ENABLED = getattr(
    settings,
    "DJANGOCMS_PICTURE_RESPONSIVE_IMAGES_ENABLED",
    # for backward compatibility, setting renamed
    getattr(settings, "DJANGOCMS_PICTURE_RESPONSIVE_IMAGES", False),
)


RESPONSIVE_IMAGE_SIZES = getattr(
    settings,
    "DJANGOCMS_PICTURE_RESPONSIVE_IMAGES_SIZES",
    # for backward compatibility, setting renamed
    getattr(
        settings,
        "DJANGOCMS_PICTURE_RESPONSIVE_IMAGES_VIEWPORT_BREAKPOINTS",
        [576, 768, 992],
    ),
)


RESPONSIVE_IMAGES_BREAKPOINT_SMALL_ID = "small"
RESPONSIVE_IMAGES_BREAKPOINT_MEDIUM_ID = "medium"
RESPONSIVE_IMAGES_BREAKPOINT_LARGE_ID = "large"

RESPONSIVE_IMAGES_BREAKPOINTS = {
    RESPONSIVE_IMAGES_BREAKPOINT_SMALL_ID: 0,
    RESPONSIVE_IMAGES_BREAKPOINT_MEDIUM_ID: getattr(
        settings, "DJANGOCMS_PICTURE_RESPONSIVE_IMAGES_BREAKPOINT_MEDIUM", 768
    ),
    RESPONSIVE_IMAGES_BREAKPOINT_LARGE_ID: getattr(
        settings, "DJANGOCMS_PICTURE_RESPONSIVE_IMAGES_BREAKPOINT_LARGE", 992
    ),
}

RESPONSIVE_IMAGES_ALTERNATIVE_FORMAT_WEBP = getattr(
    settings,
    "DJANGOCMS_PICTURE_RESPONSIVE_IMAGES_ALTERNATIVE_FORMAT_WEBP",
    False,
)
