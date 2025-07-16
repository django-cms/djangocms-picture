"""
Form fields for djangocms-picture.

This module provides form fields and widgets for the reusable picture functionality.
"""
import json

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from ..backends import backend_registry
from . import PictureData


class PictureFormField(forms.Field):
    """
    Form field for picture configuration.

    This field provides a comprehensive interface for configuring all
    picture-related options including image selection, dimensions,
    cropping, links, and accessibility features.
    """

    def __init__(self, backend=None, responsive=True, breakpoints=None,
                 formats=None, allow_links=True, alignment_choices=None,
                 max_size=None, **kwargs):
        """
        Initialize PictureFormField.

        Args:
            backend: Backend name to use
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
        self.breakpoints = breakpoints or [576, 768, 992, 1200]
        self.formats = formats or ['webp', 'jpeg', 'png']
        self.allow_links = allow_links
        self.alignment_choices = alignment_choices or [
            ('left', _('Left')),
            ('center', _('Center')),
            ('right', _('Right')),
        ]
        self.max_size = max_size

        # Set widget based on backend
        kwargs.setdefault('widget', self._get_widget())
        kwargs.setdefault('required', False)

        super().__init__(**kwargs)

    def _get_widget(self):
        """Get the appropriate widget for this field."""
        from ..widgets import PictureWidget

        return PictureWidget(
            backend=self.backend_name,
            responsive=self.responsive,
            breakpoints=self.breakpoints,
            formats=self.formats,
            allow_links=self.allow_links,
            alignment_choices=self.alignment_choices,
            max_size=self.max_size,
        )

    def get_backend(self):
        """Get the image backend for this field."""
        return backend_registry.get_backend(self.backend_name)

    def to_python(self, value):
        """Convert form input to Python object."""
        if value is None or value == '':
            return None

        if isinstance(value, PictureData):
            return value

        if isinstance(value, str):
            if not value.strip():
                return None

            try:
                # Try to parse as JSON
                data = json.loads(value)
                return PictureData(data)
            except (json.JSONDecodeError, TypeError):
                # If not JSON, might be a simple image reference
                picture_data = PictureData()
                picture_data.image_reference = value
                return picture_data

        if isinstance(value, dict):
            return PictureData(value)

        # Handle file upload
        if hasattr(value, 'read'):
            # This is a file upload, save it using the backend
            backend = self.get_backend()
            try:
                backend.validate_image(value, max_size=self.max_size)
                # Note: We can't save the image here without a model instance
                # The widget/form will handle this
                picture_data = PictureData()
                picture_data.data['uploaded_file'] = value  # Temporary storage
                return picture_data
            except ValidationError:
                raise

        return None

    def validate(self, value):
        """Validate the field value."""
        # Check required field first
        if self.required and (not value or not bool(value)):
            raise ValidationError(_('This field is required.'))

        if value and isinstance(value, PictureData):
            # Validate link configuration
            if value.link_url and value.link_page_id:
                raise ValidationError(_('Cannot have both external URL and page link.'))

            # Validate dimensions
            if value.width is not None and value.width <= 0:
                raise ValidationError(_('Width must be positive.'))
            if value.height is not None and value.height <= 0:
                raise ValidationError(_('Height must be positive.'))

    def clean(self, value):
        """Clean and validate the field value."""
        value = self.to_python(value)
        self.validate(value)
        return value


class ImageSelectionField(forms.Field):
    """
    Field for selecting images from different sources.

    This field handles image selection from filer, file upload,
    or external URL depending on the backend configuration.
    """

    def __init__(self, backend=None, **kwargs):
        """
        Initialize image selection field.

        Args:
            backend: Backend name to use
            **kwargs: Additional field options
        """
        self.backend_name = backend
        kwargs.setdefault('required', False)
        super().__init__(**kwargs)

    def get_backend(self):
        """Get the image backend for this field."""
        return backend_registry.get_backend(self.backend_name)

    def to_python(self, value):
        """Convert form input to Python object."""
        if not value:
            return None

        self.get_backend()

        # Handle file upload
        if hasattr(value, 'read'):
            return value  # Return the uploaded file

        # Handle existing image reference
        if isinstance(value, str):
            return value

        return value

    def validate(self, value):
        """Validate the uploaded image."""
        super().validate(value)

        if value and hasattr(value, 'read'):
            backend = self.get_backend()
            backend.validate_image(value)


# Export commonly used fields
__all__ = ['PictureFormField', 'ImageSelectionField']
