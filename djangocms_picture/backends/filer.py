"""
Filer backend for djangocms-picture.

This backend provides integration with django-filer for image management.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from easy_thumbnails.files import get_thumbnailer
from filer.fields.image import FilerImageField
from filer.models import ThumbnailOption

from . import ImageBackend


class FilerImageBackend(ImageBackend):
    """
    Backend that uses django-filer for image storage and processing.

    This backend maintains compatibility with the existing Picture plugin
    while providing the new backend interface.
    """

    def save_image(self, image_file, instance, field_name, **options):
        """
        Save image using django-filer.

        Args:
            image_file: The uploaded image file
            instance: Model instance containing the field
            field_name: Name of the field
            **options: Additional options

        Returns:
            Filer Image instance
        """
        from filer.models import Image

        # Create or get existing filer image
        if hasattr(image_file, 'file'):
            # This is a Filer image already
            return image_file

        # Create new filer image
        filer_image = Image.objects.create(
            original_filename=getattr(image_file, 'name', 'uploaded_image'),
            file=image_file,
        )
        return filer_image

    def get_image_url(self, image_reference, size_options=None, **kwargs):
        """
        Get URL for filer image with optional resizing.

        Args:
            image_reference: Filer Image instance
            size_options: Dict with size/crop options

        Returns:
            Image URL string
        """
        if not image_reference:
            return ''

        # Return original image URL if no sizing needed
        if not size_options:
            return image_reference.url

        # Use easy-thumbnails for resizing
        thumbnailer = get_thumbnailer(image_reference)

        thumbnail_options = {}
        if 'size' in size_options:
            thumbnail_options['size'] = size_options['size']
        if 'crop' in size_options:
            thumbnail_options['crop'] = size_options['crop']
        if 'upscale' in size_options:
            thumbnail_options['upscale'] = size_options['upscale']
        if 'quality' in size_options:
            thumbnail_options['quality'] = size_options['quality']

        # Add subject location if available
        if hasattr(image_reference, 'subject_location') and image_reference.subject_location:
            thumbnail_options['subject_location'] = image_reference.subject_location

        try:
            thumbnail = thumbnailer.get_thumbnail(thumbnail_options)
            return thumbnail.url
        except Exception:
            # Fallback to original image if thumbnail generation fails
            return image_reference.url

    def get_srcset_data(self, image_reference, breakpoints, **kwargs):
        """
        Generate responsive srcset data for filer image.

        Args:
            image_reference: Filer Image instance
            breakpoints: List of viewport breakpoints

        Returns:
            List of (width, url) tuples for srcset
        """
        if not image_reference or not breakpoints:
            return []

        srcset = []
        thumbnailer = get_thumbnailer(image_reference)

        # Get base options from kwargs
        crop = kwargs.get('crop', False)
        quality = kwargs.get('quality', 90)

        for width in breakpoints:
            try:
                thumbnail_options = {
                    'size': (width, width),  # Square for now, could be improved
                    'crop': crop,
                    'quality': quality,
                }

                # Add subject location if available
                if hasattr(image_reference, 'subject_location') and image_reference.subject_location:
                    thumbnail_options['subject_location'] = image_reference.subject_location

                thumbnail = thumbnailer.get_thumbnail(thumbnail_options)
                srcset.append((int(width), thumbnail.url))
            except Exception:
                # Skip this breakpoint if thumbnail generation fails
                continue

        return srcset

    def delete_image(self, image_reference):
        """
        Delete filer image and its thumbnails.

        Args:
            image_reference: Filer Image instance
        """
        if image_reference:
            # Delete thumbnails first
            try:
                thumbnailer = get_thumbnailer(image_reference)
                thumbnailer.delete_thumbnails()
            except Exception:
                pass  # Continue even if thumbnail deletion fails

            # Delete the filer image
            image_reference.delete()

    def get_image_info(self, image_reference):
        """
        Get metadata about filer image.

        Args:
            image_reference: Filer Image instance

        Returns:
            Dict with image metadata
        """
        if not image_reference:
            return {}

        info = {
            'width': getattr(image_reference, 'width', None),
            'height': getattr(image_reference, 'height', None),
            'format': getattr(image_reference, 'file_type', '').upper(),
            'size': getattr(image_reference, 'size', 0),
            'alt_text': getattr(image_reference, 'default_alt_text', ''),
            'caption': getattr(image_reference, 'default_caption', ''),
            'filename': getattr(image_reference, 'original_filename', ''),
            'label': getattr(image_reference, 'label', ''),
        }

        return info

    def validate_image(self, image_file, **options):
        """
        Validate filer image.

        Args:
            image_file: Image file to validate
            **options: Validation options

        Raises:
            ValidationError: If validation fails
        """
        # Basic file type validation
        allowed_types = options.get('allowed_types', ['jpeg', 'jpg', 'png', 'gif', 'webp'])

        if hasattr(image_file, 'content_type'):
            content_type = image_file.content_type.lower()
            if not any(allowed_type in content_type for allowed_type in allowed_types):
                raise ValidationError(f"File type not allowed. Allowed types: {', '.join(allowed_types)}")

        # File size validation
        max_size = options.get('max_size')  # in bytes
        if max_size and hasattr(image_file, 'size') and image_file.size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise ValidationError(f"File too large. Maximum size: {max_size_mb:.1f}MB")

        # Image dimension validation
        if hasattr(image_file, 'width') and hasattr(image_file, 'height'):
            min_width = options.get('min_width', 0)
            min_height = options.get('min_height', 0)
            max_width = options.get('max_width')
            max_height = options.get('max_height')

            if image_file.width < min_width:
                raise ValidationError(f"Image width too small. Minimum: {min_width}px")
            if image_file.height < min_height:
                raise ValidationError(f"Image height too small. Minimum: {min_height}px")
            if max_width and image_file.width > max_width:
                raise ValidationError(f"Image width too large. Maximum: {max_width}px")
            if max_height and image_file.height > max_height:
                raise ValidationError(f"Image height too large. Maximum: {max_height}px")

    def get_field_class(self):
        """
        Get the Django model field class for this backend.

        Returns:
            FilerImageField class
        """
        return FilerImageField

    def get_field_kwargs(self, **options):
        """
        Get kwargs for the field constructor.

        Args:
            **options: Field options

        Returns:
            Dict of field kwargs
        """
        kwargs = {
            'blank': options.get('blank', True),
            'null': options.get('null', True),
            'on_delete': options.get('on_delete', 'SET_NULL'),
            'related_name': options.get('related_name', '+'),
        }

        # Convert on_delete string to models constant
        if isinstance(kwargs['on_delete'], str):
            from django.db import models
            kwargs['on_delete'] = getattr(models, kwargs['on_delete'])

        return kwargs
