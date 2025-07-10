"""
Backend abstraction system for djangocms-picture.

This module provides a pluggable backend system to support different
image storage and processing solutions.
"""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string


class ImageBackend:
    """
    Base class for image backends.
    
    Backends handle image storage, processing, and URL generation
    for different image management systems.
    """
    
    def save_image(self, image_file, instance, field_name, **options):
        """
        Save an uploaded image file.
        
        Args:
            image_file: The uploaded image file object
            instance: The model instance containing the field
            field_name: Name of the field in the model
            **options: Additional backend-specific options
            
        Returns:
            Reference to the saved image (backend-specific format)
        """
        raise NotImplementedError("Subclasses must implement save_image()")
    
    def get_image_url(self, image_reference, size_options=None, **kwargs):
        """
        Get the URL for an image with optional sizing.
        
        Args:
            image_reference: Backend-specific image reference
            size_options: Dict with size/crop options
            **kwargs: Additional options
            
        Returns:
            String URL to the image
        """
        raise NotImplementedError("Subclasses must implement get_image_url()")
    
    def get_srcset_data(self, image_reference, breakpoints, **kwargs):
        """
        Generate responsive image srcset data.
        
        Args:
            image_reference: Backend-specific image reference
            breakpoints: List of viewport breakpoints
            **kwargs: Additional options
            
        Returns:
            List of tuples: [(width, url), ...]
        """
        raise NotImplementedError("Subclasses must implement get_srcset_data()")
    
    def delete_image(self, image_reference):
        """
        Delete an image and its variants.
        
        Args:
            image_reference: Backend-specific image reference
        """
        raise NotImplementedError("Subclasses must implement delete_image()")
    
    def get_image_info(self, image_reference):
        """
        Get metadata about an image.
        
        Args:
            image_reference: Backend-specific image reference
            
        Returns:
            Dict with keys: width, height, format, size, alt_text, etc.
        """
        raise NotImplementedError("Subclasses must implement get_image_info()")
    
    def validate_image(self, image_file, **options):
        """
        Validate an image file before saving.
        
        Args:
            image_file: The image file to validate
            **options: Validation options
            
        Raises:
            ValidationError: If image is invalid
        """
        pass  # Default implementation does no validation


class BackendRegistry:
    """Registry for managing available image backends."""
    
    def __init__(self):
        self._backends = {}
        self._loaded = False
    
    def _load_backends(self):
        """Load backends from Django settings."""
        if self._loaded:
            return
            
        backend_settings = getattr(settings, 'DJANGOCMS_PICTURE_BACKENDS', {})
        
        # If no backends are configured, register default ones
        if not backend_settings:
            _register_default_backends()
            return
        
        for name, backend_path in backend_settings.items():
            try:
                backend_class = import_string(backend_path)
                self._backends[name] = backend_class
            except ImportError as e:
                # For now, just skip missing backends instead of raising an error
                # This allows the system to work even if some backends are not available
                import logging
                logging.warning(f"Could not import backend '{name}' from '{backend_path}': {e}")
        
        self._loaded = True
    
    def get_backend(self, name=None):
        """
        Get a backend instance by name.
        
        Args:
            name: Backend name, defaults to DJANGOCMS_PICTURE_DEFAULT_BACKEND
            
        Returns:
            Backend instance
        """
        self._load_backends()
        
        if name is None:
            name = getattr(settings, 'DJANGOCMS_PICTURE_DEFAULT_BACKEND', 'filer')
        
        if name not in self._backends:
            available = ', '.join(self._backends.keys())
            raise ImproperlyConfigured(
                f"Backend '{name}' not found. Available backends: {available}"
            )
        
        return self._backends[name]()
    
    def get_available_backends(self):
        """Get list of available backend names."""
        self._load_backends()
        return list(self._backends.keys())


# Global registry instance
backend_registry = BackendRegistry()


# Register default backends on import
def _register_default_backends():
    """Register the default backends that are available."""
    try:
        from .filer import FilerImageBackend
        backend_registry._backends['filer'] = FilerImageBackend
    except ImportError:
        pass  # Filer not available
    
    # Mark as loaded so it doesn't try to load from settings
    backend_registry._loaded = True


# Don't auto-register default backends on import to avoid Django setup issues
# They will be registered when first accessed through _load_backends() 