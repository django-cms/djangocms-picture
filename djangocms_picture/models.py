"""
Enables the user to add an "Image" plugin that displays an image
using the HTML <img> tag.
"""
from collections.abc import Mapping
from typing import Any

from cms.models import CMSPlugin
from cms.models.fields import PageField
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from djangocms_attributes_field.fields import AttributesField
from filer.models import ThumbnailOption

from .backends import (
    BaseImageAsset,
    BasePictureBackend,
    ImageAttribution,
    PictureBackendError,
    PictureReference,
    PictureSourceDescriptor,
    Rendition,
    RenditionSpec,
    StoredPictureSource,
    UnavailablePictureBackend,
    get_backend_for_instance,
)
from .linking import DJANGOCMS_LINK_ENABLED, PictureLinkField, resolve_picture_link
from .rendering import build_srcset, calculate_size


# add setting for picture alignment, renders a class or inline styles
# depending on your template setup
def get_alignment():
    alignment = getattr(
        settings,
        'DJANGOCMS_PICTURE_ALIGN',
        (
            ('left', _('Align left')),
            ('right', _('Align right')),
            ('center', _('Align center')),
        )
    )
    return alignment


# Add additional choices through the ``settings.py``.
def get_templates():
    choices = [
        ('default', _('Default')),
    ]
    choices += getattr(
        settings,
        'DJANGOCMS_PICTURE_TEMPLATES',
        [],
    )
    return choices


# use golden ration as default (https://en.wikipedia.org/wiki/Golden_ratio)
PICTURE_RATIO = getattr(settings, 'DJANGOCMS_PICTURE_RATIO', 1.6180)

# required for backwards compability
PICTURE_ALIGNMENT = get_alignment()

LINK_TARGET = (
    ('_blank', _('Open in new window')),
    ('_self', _('Open in same window')),
    ('_parent', _('Delegate to parent')),
    ('_top', _('Delegate to top')),
)

RESPONSIVE_IMAGE_CHOICES = (
    ('inherit', _('Let settings.DJANGOCMS_PICTURE_RESPONSIVE_IMAGES decide')),
    ('yes', _('Yes')),
    ('no', _('No')),
)


class AbstractPicture(CMSPlugin):
    """
    Renders an image with the option of adding a link
    """
    template = models.CharField(
        verbose_name=_('Template'),
        choices=get_templates(),
        default=get_templates()[0][0],
        max_length=255,
    )
    backend = models.CharField(
        verbose_name=_("Image source"),
        max_length=32,
        default="filer",
    )
    picture_content_type = models.ForeignKey(
        ContentType,
        verbose_name=_("Image model"),
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    picture_object_id = models.CharField(
        verbose_name=_("Image object ID"),
        blank=True,
        null=True,
        max_length=255,
    )
    picture = GenericForeignKey(
        "picture_content_type",
        "picture_object_id",
        for_concrete_model=False,
    )
    picture_config = models.JSONField(
        verbose_name=_("Image source configuration"),
        blank=True,
        default=dict,
    )
    image_source = PictureSourceDescriptor()
    width = models.PositiveIntegerField(
        verbose_name=_('Width'),
        blank=True,
        null=True,
        help_text=_(
            'The image width as number in pixels. '
            'Example: "720" and not "720px".'
        ),
    )
    height = models.PositiveIntegerField(
        verbose_name=_('Height'),
        blank=True,
        null=True,
        help_text=_(
            'The image height as number in pixels. '
            'Example: "720" and not "720px".'
        ),
    )
    alignment = models.CharField(
        verbose_name=_('Alignment'),
        choices=get_alignment(),
        blank=True,
        max_length=255,
        help_text=_('Aligns the image according to the selected option.'),
    )
    caption_text = models.TextField(
        verbose_name=_('Caption text'),
        blank=True,
        null=True,
        help_text=_('Provide a description, attribution, copyright or other information.')
    )
    attributes = AttributesField(
        verbose_name=_('Attributes'),
        blank=True,
        excluded_keys=['src', 'width', 'height'],
    )
    # link models
    link_url = models.URLField(
        verbose_name=_('External URL'),
        blank=True,
        null=True,
        max_length=2040,
        help_text=_('Wraps the image in a link to an external URL.'),
    )
    link_page = PageField(
        verbose_name=_('Internal URL'),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text=_('Wraps the image in a link to an internal (page) URL.'),
    )
    link_target = models.CharField(
        verbose_name=_('Link target'),
        choices=LINK_TARGET,
        blank=True,
        max_length=255,
    )
    link_attributes = AttributesField(
        verbose_name=_('Link attributes'),
        blank=True,
        excluded_keys=['href', 'target'],
    )
    link = PictureLinkField(
        verbose_name=_('Link'),
        blank=True,
    )
    # cropping models
    # active per default
    use_automatic_scaling = models.BooleanField(
        verbose_name=_('Automatic scaling'),
        blank=True,
        default=True,
        help_text=_('Uses the placeholder dimensions to automatically calculate the size.'),
    )
    # ignores all other cropping options
    # throws validation error if other cropping options are selected
    use_no_cropping = models.BooleanField(
        verbose_name=_('Use original image'),
        blank=True,
        default=False,
        help_text=_('Outputs the raw image without cropping.'),
    )
    # upscale and crop work together
    # throws validation error if other cropping options are selected
    use_crop = models.BooleanField(
        verbose_name=_('Crop image'),
        blank=True,
        default=False,
        help_text=_('Crops the image according to the thumbnail settings provided in the template.'),
    )
    use_upscale = models.BooleanField(
        verbose_name=_('Upscale image'),
        blank=True,
        default=False,
        help_text=_('Upscales the image to the size of the thumbnail settings in the template.')
    )
    use_responsive_image = models.CharField(
        verbose_name=_('Use responsive image'),
        max_length=7,
        choices=RESPONSIVE_IMAGE_CHOICES,
        default=RESPONSIVE_IMAGE_CHOICES[0][0],
        help_text=_(
            'Uses responsive image technique to choose better image to display based upon screen viewport. '
            'This configuration only applies to uploaded images (external pictures will not be affected). '
        )
    )
    # overrides all other options
    # throws validation error if other cropping options are selected
    thumbnail_options = models.ForeignKey(
        ThumbnailOption,
        verbose_name=_('Thumbnail options'),
        blank=True,
        null=True,
        help_text=_('Overrides width, height, and crop; scales up to the provided preset dimensions.'),
        on_delete=models.CASCADE,
    )

    # Add an app namespace to related_name to avoid field name clashes
    # with any other plugins that have a field with the same name as the
    # lowercase of the class name of this model.
    # https://github.com/divio/django-cms/issues/5030
    cmsplugin_ptr = models.OneToOneField(
        CMSPlugin,
        related_name='%(app_label)s_%(class)s',
        parent_link=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(
                fields=("picture_content_type", "picture_object_id"),
                name="dcp_picture_object_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(picture_content_type__isnull=True, picture_object_id__isnull=True)
                    | models.Q(picture_content_type__isnull=False, picture_object_id__isnull=False)
                ),
                name="dcp_picture_object_pair",
            ),
        ]

    @property
    def picture_id(self) -> Any | None:
        """Return the typed object ID used by historical filer integrations."""

        if self.picture_object_id is None:
            return None
        content_type = self.picture_content_type
        model = content_type.model_class() if content_type is not None else None
        if model is not None:
            return model._meta.pk.to_python(self.picture_object_id)
        return self.picture_object_id

    @picture_id.setter
    def picture_id(self, value: Any | None) -> None:
        """Accept historical filer ID assignment while using generic storage."""

        if value is None:
            if self.backend == "filer":
                self.image_source = StoredPictureSource(backend="filer")
            else:
                self.picture = None
            return

        from filer.utils.loader import load_model

        image_model = load_model(settings.FILER_IMAGE_MODEL)
        content_type = ContentType.objects.get_for_model(
            image_model,
            for_concrete_model=False,
        )
        identifier = str(image_model._meta.pk.to_python(value))
        self.image_source = StoredPictureSource(
            backend="filer",
            reference=PictureReference(backend="filer", id=identifier),
            content_type_id=content_type.pk,
            object_id=identifier,
        )

    @property
    def external_picture(self) -> str | None:
        """Expose URL backend values through the historical public attribute."""

        source = self.image_source
        reference = source.reference
        return reference.id if reference is not None and reference.backend == "url" else None

    @external_picture.setter
    def external_picture(self, value: str | None) -> None:
        if value:
            image = self.picture
            snapshot = {
                "width": getattr(image, "width", None),
                "height": getattr(image, "height", None),
                "alt_text": getattr(image, "default_alt_text", "") or "",
            }
            self.image_source = StoredPictureSource(
                backend="url",
                reference=PictureReference(
                    backend="url",
                    id=str(value),
                    snapshot=snapshot,
                ),
            )
        elif getattr(self, "backend", None) == "url":
            self.image_source = StoredPictureSource(backend="url")

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.backend == "filer" and self.picture is not None and not self.picture_config:
            self.image_source = StoredPictureSource(
                backend="filer",
                reference=PictureReference(
                    backend="filer",
                    id=str(self.picture.pk),
                ),
                source_object=self.picture,
            )
        if DJANGOCMS_LINK_ENABLED:
            self.sync_legacy_link_fields()
            update_fields = kwargs.get("update_fields")
            if update_fields is not None and "link" in update_fields:
                kwargs["update_fields"] = {*update_fields, "link_url", "link_page"}
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        label = getattr(self.picture, "label", None) or getattr(self.picture, "name", None)
        if label:
            return str(label)
        return str(self.pk)

    @property
    def picture_backend(self) -> BasePictureBackend:
        """Return the backend selected by the instance's persisted reference."""

        return get_backend_for_instance(self)

    @property
    def image_asset(self) -> BaseImageAsset | None:
        """Return a backend-neutral image asset for rendering and metadata."""

        return self.picture_backend.get_asset(self)

    @property
    def picture_reference(self) -> PictureReference | None:
        asset = self.image_asset
        return asset.reference if asset else None

    @property
    def image_alt_text(self) -> str:
        # Keep the historical filer fallback when an external URL overrides a
        # selected image. Other backends expose their own fallback through info.
        if self.picture_backend.alias == "url" and self.picture and self.picture.default_alt_text:
            return self.picture.default_alt_text
        asset = self.image_asset
        return asset.info.alt_text if asset else ''

    @property
    def image_attribution(self) -> ImageAttribution | None:
        """Return provider-required linked credit, when present."""

        asset = self.image_asset
        return asset.attribution if asset else None

    def get_short_description(self) -> str:
        asset = self.image_asset
        if asset and asset.info.label:
            return asset.info.label
        return gettext('<file is missing>')

    def copy_relations(self, oldinstance: "AbstractPicture") -> None:
        backend = get_backend_for_instance(oldinstance)
        self.backend = backend.alias
        backend.copy_reference(oldinstance, self)

    def get_size(
        self,
        width: int | float | None = None,
        height: int | float | None = None,
    ) -> dict[str, Any]:
        crop = self.use_crop
        upscale = self.use_upscale
        # use field thumbnail settings
        if self.thumbnail_options:
            width = self.thumbnail_options.width
            height = self.thumbnail_options.height
            crop = self.thumbnail_options.crop
            upscale = self.thumbnail_options.upscale
        elif not self.use_automatic_scaling:
            width = self.width
            height = self.height

        asset = self.image_asset
        spec = calculate_size(
            asset.info if asset else None,
            width=width,
            height=height,
            crop=crop,
            upscale=upscale,
            picture_ratio=PICTURE_RATIO,
        )

        options = {
            'size': (spec.width, spec.height),
            'crop': spec.crop,
            'upscale': spec.upscale,
        }
        return options

    def get_link(self) -> str | bool:
        if DJANGOCMS_LINK_ENABLED and self.link:
            return resolve_picture_link(self.link) or False
        if self.link_url:
            return self.link_url
        elif self.link_page_id:
            return self.link_page.get_absolute_url(language=self.language)
        elif self.external_picture:
            return self.external_picture
        return False

    def get_legacy_link_value(self) -> dict[str, str]:
        """Return legacy link columns in djangocms-link's JSON representation."""

        if self.link_url:
            return {"external_link": self.link_url}
        if self.link_page_id:
            return {"internal_link": f"cms.page:{self.link_page_id}"}
        return {}

    def sync_legacy_link_fields(self) -> None:
        """Mirror link values that the legacy URL and page fields can represent."""

        self.link_url = None
        self.link_page_id = None
        if not isinstance(self.link, Mapping):
            return

        external_link = self.link.get("external_link")
        if isinstance(external_link, str) and external_link:
            link_url_field = self._meta.get_field("link_url")
            try:
                URLValidator(schemes=("http", "https"))(external_link)
            except ValidationError:
                pass
            else:
                if link_url_field.max_length is None or len(external_link) <= link_url_field.max_length:
                    self.link_url = external_link
                    return

        internal_link = self.link.get("internal_link")
        if not isinstance(internal_link, str):
            return
        model_label, separator, raw_pk = internal_link.partition(":")
        if model_label.lower() != "cms.page" or not separator or not raw_pk:
            return
        link_page_field = self._meta.get_field("link_page")
        try:
            page_pk = link_page_field.target_field.to_python(raw_pk)
        except (TypeError, ValueError, ValidationError):
            return
        page_model = link_page_field.remote_field.model
        if page_model._base_manager.filter(pk=page_pk).exists():
            self.link_page_id = page_pk

    def clean(self) -> None:
        backend = self.picture_backend
        try:
            backend.validate_storage(self)
        except PictureBackendError as error:
            raise ValidationError(str(error)) from error

        # there can be only one link type
        if not DJANGOCMS_LINK_ENABLED and self.link_url and self.link_page_id:
            raise ValidationError(
                gettext(
                    'You have given both external and internal links. '
                    'Only one option is allowed.'
                )
            )

        # you shall only set one image kind
        source = self.image_source
        if (
            not isinstance(backend, UnavailablePictureBackend)
            and source.reference is None
            and source.object_id is None
        ):
            raise ValidationError(
                gettext(
                    'You need to add either an image, '
                    'or a URL linking to an external image.'
                )
            )

        # certain cropping options do not work together, the following
        # list defines the disallowed options used in the ``clean`` method
        invalid_option_pairs = [
            ('use_automatic_scaling', 'use_no_cropping'),
            ('use_automatic_scaling', 'thumbnail_options'),
            ('use_no_cropping', 'use_crop'),
            ('use_no_cropping', 'use_upscale'),
            ('use_no_cropping', 'thumbnail_options'),
            ('thumbnail_options', 'use_crop'),
            ('thumbnail_options', 'use_upscale'),
        ]
        # invalid_option_pairs
        invalid_option_pair = None

        for pair in invalid_option_pairs:
            if getattr(self, pair[0]) and getattr(self, pair[1]):
                invalid_option_pair = pair
                break

        if invalid_option_pair:
            message = gettext(
                'Invalid cropping settings. '
                'You cannot combine "{field_a}" with "{field_b}".'
            )
            message = message.format(
                field_a=self._meta.get_field(invalid_option_pair[0]).verbose_name,
                field_b=self._meta.get_field(invalid_option_pair[1]).verbose_name,
            )
            raise ValidationError(message)

    @property
    def is_responsive_image(self) -> bool:
        asset = self.image_asset
        if not asset or not self.picture_backend.capabilities.responsive:
            return False
        if self.use_responsive_image == 'inherit':
            return getattr(settings, 'DJANGOCMS_PICTURE_RESPONSIVE_IMAGES', False)
        return self.use_responsive_image == 'yes'

    @property
    def img_srcset_data(self) -> list[tuple[int, Rendition]] | None:
        asset = self.image_asset
        if not (asset and self.is_responsive_image):
            return None

        picture_options = self.get_size(self.width, self.height)
        picture_width = picture_options['size'][0]
        breakpoints = getattr(
            settings,
            'DJANGOCMS_PICTURE_RESPONSIVE_IMAGES_VIEWPORT_BREAKPOINTS',
            [576, 768, 992],
        )
        return build_srcset(
            asset,
            widths=breakpoints,
            width=picture_width,
            crop=picture_options['crop'] and self.picture_backend.capabilities.crop,
        )

    @property
    def img_src(self) -> str:
        asset = self.image_asset
        # The image can be empty, for example when it is removed from filer.
        if not asset:
            return ''
        if self.use_no_cropping:
            return asset.get_original().url

        picture_options = self.get_size(
            width=self.width or 0,
            height=self.height or 0,
        )
        capabilities = self.picture_backend.capabilities
        return asset.get_rendition(
            RenditionSpec(
                width=picture_options['size'][0],
                height=picture_options['size'][1],
                crop=picture_options['crop'] and capabilities.crop,
                upscale=picture_options['upscale'] and capabilities.upscale,
            )
        ).url


class Picture(AbstractPicture):

    class Meta(AbstractPicture.Meta):
        abstract = False
