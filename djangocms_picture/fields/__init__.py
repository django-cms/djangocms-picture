"""
Reusable picture fields for djangocms-picture.

This module provides PictureField and PictureFormField that can be used
in any Django model or form, not just CMS plugins.
"""
import json

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from ..backends import backend_registry


class PictureData:
    """
    Container for picture configuration data.

    This class encapsulates all the image-related settings like dimensions,
    cropping, links, etc. in a structured way.
    """

    def __init__(self, data=None):
        """
        Initialize picture data.

        Args:
            data: Dict of picture configuration or JSON string
        """
        if isinstance(data, str):
            try:
                data = json.loads(data) if data else {}
            except json.JSONDecodeError:
                data = {}
        elif data is None:
            data = {}

        self.data = data

    # Image properties
    @property
    def image_reference(self):
        """Get the backend-specific image reference."""
        return self.data.get('image_reference')

    @image_reference.setter
    def image_reference(self, value):
        """Set the backend-specific image reference."""
        self.data['image_reference'] = value

    @property
    def external_url(self):
        """Get external image URL."""
        return self.data.get('external_url', '')

    @external_url.setter
    def external_url(self, value):
        """Set external image URL."""
        self.data['external_url'] = value

    # Dimension properties
    @property
    def width(self):
        """Get image width in pixels."""
        return self.data.get('width')

    @width.setter
    def width(self, value):
        """Set image width in pixels."""
        if value is not None:
            self.data['width'] = int(value)
        else:
            self.data.pop('width', None)

    @property
    def height(self):
        """Get image height in pixels."""
        return self.data.get('height')

    @height.setter
    def height(self, value):
        """Set image height in pixels."""
        if value is not None:
            self.data['height'] = int(value)
        else:
            self.data.pop('height', None)

    # Responsive properties
    @property
    def responsive(self):
        """Check if responsive images are enabled."""
        return self.data.get('responsive', True)

    @responsive.setter
    def responsive(self, value):
        """Enable/disable responsive images."""
        self.data['responsive'] = bool(value)

    @property
    def breakpoints(self):
        """Get responsive breakpoints."""
        return self.data.get('breakpoints', [576, 768, 992, 1200])

    @breakpoints.setter
    def breakpoints(self, value):
        """Set responsive breakpoints."""
        self.data['breakpoints'] = list(value) if value else []

    # Cropping properties
    @property
    def crop(self):
        """Check if image cropping is enabled."""
        return self.data.get('crop', False)

    @crop.setter
    def crop(self, value):
        """Enable/disable image cropping."""
        self.data['crop'] = bool(value)

    @property
    def upscale(self):
        """Check if image upscaling is enabled."""
        return self.data.get('upscale', False)

    @upscale.setter
    def upscale(self, value):
        """Enable/disable image upscaling."""
        self.data['upscale'] = bool(value)

    # Link properties
    @property
    def link_url(self):
        """Get external link URL."""
        return self.data.get('link_url', '')

    @link_url.setter
    def link_url(self, value):
        """Set external link URL."""
        self.data['link_url'] = value or ''

    @property
    def link_page_id(self):
        """Get internal page link ID."""
        return self.data.get('link_page_id')

    @link_page_id.setter
    def link_page_id(self, value):
        """Set internal page link ID."""
        if value is not None:
            self.data['link_page_id'] = int(value)
        else:
            self.data.pop('link_page_id', None)

    @property
    def link_target(self):
        """Get link target."""
        return self.data.get('link_target', '')

    @link_target.setter
    def link_target(self, value):
        """Set link target."""
        self.data['link_target'] = value or ''

    # Accessibility properties
    @property
    def alt_text(self):
        """Get alt text."""
        return self.data.get('alt_text', '')

    @alt_text.setter
    def alt_text(self, value):
        """Set alt text."""
        self.data['alt_text'] = value or ''

    @property
    def caption(self):
        """Get caption text."""
        return self.data.get('caption', '')

    @caption.setter
    def caption(self, value):
        """Set caption text."""
        self.data['caption'] = value or ''

    # Style properties
    @property
    def alignment(self):
        """Get image alignment."""
        return self.data.get('alignment', '')

    @alignment.setter
    def alignment(self, value):
        """Set image alignment."""
        self.data['alignment'] = value or ''

    @property
    def css_classes(self):
        """Get CSS classes."""
        return self.data.get('css_classes', '')

    @css_classes.setter
    def css_classes(self, value):
        """Set CSS classes."""
        self.data['css_classes'] = value or ''

    def to_json(self):
        """Convert to JSON string."""
        return json.dumps(self.data)

    def __bool__(self):
        """Check if picture data has content."""
        return bool(self.image_reference or self.external_url)

    def __str__(self):
        """String representation."""
        if self.external_url:
            return f"External: {self.external_url}"
        elif self.image_reference:
            return f"Image: {self.image_reference}"
        return "Empty Picture"

    def __eq__(self, other):
        """Check equality with another PictureData object."""
        if not isinstance(other, PictureData):
            return False
        return self.data == other.data

    def __hash__(self):
        """Make PictureData hashable."""
        return hash(self.to_json())


class PictureField(models.JSONField):
    """
    A reusable picture field that can be used in any Django model.

    This field stores picture configuration as JSON and uses the backend
    system to handle image storage and processing.
    """

    description = _("Picture with configuration options")

    def __init__(self, backend=None, responsive=True, breakpoints=None,
                 formats=None, allow_links=True, alignment_choices=None,
                 max_size=None, **kwargs):
        """
        Initialize PictureField.

        Args:
            backend: Backend name to use (defaults to settings)
            responsive: Enable responsive images
            breakpoints: List of responsive breakpoints
            formats: List of supported image formats
            allow_links: Allow linking images
            alignment_choices: List of alignment options
            max_size: Maximum file size in bytes
            **kwargs: Additional field options
        """
        self.backend_name = backend
        self.responsive = responsive
        self.breakpoints = breakpoints or getattr(
            settings, 'DJANGOCMS_PICTURE_RESPONSIVE_BREAKPOINTS', [576, 768, 992, 1200]
        )
        self.formats = formats or ['webp', 'jpeg', 'png']
        self.allow_links = allow_links
        self.alignment_choices = alignment_choices
        self.max_size = max_size

        # Set default for JSONField
        kwargs.setdefault('default', dict)
        kwargs.setdefault('blank', True)

        super().__init__(**kwargs)

    def get_backend(self):
        """Get the image backend for this field."""
        return backend_registry.get_backend(self.backend_name)

    def deconstruct(self):
        """
        Return enough information to recreate the field.

        This is used for migrations.
        """
        name, path, args, kwargs = super().deconstruct()

        # Add custom arguments
        if self.backend_name is not None:
            kwargs['backend'] = self.backend_name
        if not self.responsive:
            kwargs['responsive'] = False
        if self.breakpoints != [576, 768, 992, 1200]:
            kwargs['breakpoints'] = self.breakpoints
        if self.formats != ['webp', 'jpeg', 'png']:
            kwargs['formats'] = self.formats
        if not self.allow_links:
            kwargs['allow_links'] = False
        if self.alignment_choices is not None:
            kwargs['alignment_choices'] = self.alignment_choices
        if self.max_size is not None:
            kwargs['max_size'] = self.max_size

        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        """Convert database value to Python object."""
        if value is None:
            return None
        return PictureData(value)

    def to_python(self, value):
        """Convert value to Python object."""
        if isinstance(value, PictureData):
            return value
        if value is None:
            return None
        return PictureData(value)

    def get_prep_value(self, value):
        """Convert Python object to database value."""
        if value is None:
            return None
        if isinstance(value, PictureData):
            return value.to_json()
        return json.dumps(value)

    def validate(self, value, model_instance):
        """Validate the field value."""
        # Skip JSONField validation for PictureData objects
        if isinstance(value, PictureData):
            # Convert to dict for JSONField validation
            dict_value = value.data if value else {}
            models.Field.validate(self, dict_value, model_instance)

            # Custom validation for PictureData
            if value is not None and value.data:  # Check if there's actual data
                # Validate that we have either an image or external URL
                if not value.image_reference and not value.external_url:
                    raise ValidationError(_('Either an image or external URL is required.'))

                # Validate that we don't have both link types
                if value.link_url and value.link_page_id:
                    raise ValidationError(_('Cannot have both external URL and page link.'))
        else:
            # For non-PictureData values, use default JSONField validation
            super().validate(value, model_instance)

    def formfield(self, **kwargs):
        """Return a form field for this model field."""
        from .forms import PictureFormField

        # Filter out JSONField-specific arguments that PictureFormField doesn't need
        json_specific_args = ['encoder', 'decoder']
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in json_specific_args}

        defaults = {
            'backend': self.backend_name,
            'responsive': self.responsive,
            'breakpoints': self.breakpoints,
            'formats': self.formats,
            'allow_links': self.allow_links,
            'alignment_choices': self.alignment_choices,
            'max_size': self.max_size,
        }
        defaults.update(filtered_kwargs)

        # Create PictureFormField directly since we're handling the arguments ourselves
        return PictureFormField(**defaults)
