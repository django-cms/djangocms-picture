"""
Widgets for djangocms-picture.

This module provides widgets for the reusable picture functionality.
"""
import json
from django import forms
from django.conf import settings
from django.forms.widgets import Media
from django.forms.utils import flatatt
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from ..backends import backend_registry


class PictureWidget(forms.Widget):
    """
    Widget for comprehensive picture configuration.
    
    This widget provides a rich interface for configuring all picture-related
    options including image selection, dimensions, cropping, links, and
    accessibility features.
    """
    
    template_name = 'djangocms_picture/widgets/picture_widget.html'
    
    def __init__(self, backend=None, responsive=True, breakpoints=None,
                 formats=None, allow_links=True, alignment_choices=None,
                 max_size=None, **kwargs):
        """
        Initialize PictureWidget.
        
        Args:
            backend: Backend name to use
            responsive: Enable responsive images
            breakpoints: List of responsive breakpoints
            formats: List of supported image formats
            allow_links: Allow linking images
            alignment_choices: List of alignment options
            max_size: Maximum file size in bytes
            **kwargs: Additional widget options
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
        
        super().__init__(**kwargs)
    
    def get_backend(self):
        """Get the image backend for this widget."""
        return backend_registry.get_backend(self.backend_name)
    
    def format_value(self, value):
        """Format the value for rendering."""
        if not value:
            return ''
        
        if hasattr(value, 'to_json'):
            return value.to_json()
        
        if isinstance(value, dict):
            return json.dumps(value)
        
        return str(value)
    
    def value_from_datadict(self, data, files, name):
        """Extract value from form data."""
        # Get the main picture data
        picture_data = data.get(name, '{}')
        
        # Handle file upload
        uploaded_file = files.get(f'{name}_file')
        if uploaded_file:
            # If there's an uploaded file, create basic picture data
            if isinstance(picture_data, str):
                try:
                    picture_data = json.loads(picture_data)
                except json.JSONDecodeError:
                    picture_data = {}
            
            # Store the uploaded file reference
            picture_data['uploaded_file'] = uploaded_file
        
        return picture_data
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget."""
        from ..fields import PictureData
        
        # Ensure attrs is a dict
        attrs = attrs or {}
        
        # Convert value to PictureData if needed
        if isinstance(value, str):
            try:
                value = PictureData(json.loads(value) if value else {})
            except json.JSONDecodeError:
                value = PictureData()
        elif not isinstance(value, PictureData):
            value = PictureData(value)
        
        # Get backend information
        backend = self.get_backend()
        
        # Prepare context for template
        context = {
            'widget': self,
            'name': name,
            'value': value,
            'attrs': attrs,
            'backend': backend,
            'backend_name': self.backend_name,
            'responsive': self.responsive,
            'breakpoints': self.breakpoints,
            'formats': self.formats,
            'allow_links': self.allow_links,
            'alignment_choices': self.alignment_choices,
            'max_size': self.max_size,
            'max_size_mb': self.max_size / (1024 * 1024) if self.max_size else None,
        }
        
        # Render template
        try:
            return render_to_string(self.template_name, context)
        except Exception:
            # Fallback to basic rendering if template is not found
            return self._render_fallback(name, value, attrs)
    
    def _render_fallback(self, name, value, attrs):
        """Fallback rendering when template is not available."""
        # Basic JSON input as fallback
        json_value = self.format_value(value)
        attrs.update({
            'type': 'hidden',
            'name': name,
            'value': json_value,
        })
        
        # Create basic HTML structure
        html = format_html(
            '<div class="djangocms-picture-widget" data-name="{}">'
            '<input{} />'
            '<div class="picture-config">'
            '<p>Picture configuration: {}</p>'
            '<label>Upload Image: <input type="file" name="{}_file" accept="image/*" /></label>'
            '</div>'
            '</div>',
            name,
            flatatt(attrs),
            json_value[:100] + '...' if len(json_value) > 100 else json_value,
            name
        )
        
        return mark_safe(html)
    
    @property
    def media(self):
        """Return media files needed for the widget."""
        css = {
            'all': [
                'djangocms_picture/css/picture-widget.css',
            ]
        }
        
        js = [
            'djangocms_picture/js/picture-widget.js',
        ]
        
        return Media(css=css, js=js)
    
    def value_omitted_from_data(self, data, files, name):
        """Check if value was omitted from data."""
        return name not in data and f'{name}_file' not in files


class SimpleImageWidget(forms.Widget):
    """
    Simple widget for just image selection.
    
    This widget provides a basic interface for selecting images
    without the full picture configuration options.
    """
    
    template_name = 'djangocms_picture/widgets/simple_image_widget.html'
    
    def __init__(self, backend=None, **kwargs):
        """
        Initialize SimpleImageWidget.
        
        Args:
            backend: Backend name to use
            **kwargs: Additional widget options
        """
        self.backend_name = backend
        super().__init__(**kwargs)
    
    def get_backend(self):
        """Get the image backend for this widget."""
        return backend_registry.get_backend(self.backend_name)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget."""
        attrs = attrs or {}
        backend = self.get_backend()
        
        context = {
            'widget': self,
            'name': name,
            'value': value,
            'attrs': attrs,
            'backend': backend,
            'backend_name': self.backend_name,
        }
        
        try:
            return render_to_string(self.template_name, context)
        except Exception:
            # Fallback to basic file input
            attrs.update({
                'type': 'file',
                'name': name,
                'accept': 'image/*',
            })
            return format_html('<input{} />', flatatt(attrs))
    
    @property
    def media(self):
        """Return media files needed for the widget."""
        css = {
            'all': [
                'djangocms_picture/css/simple-image-widget.css',
            ]
        }
        
        js = [
            'djangocms_picture/js/simple-image-widget.js',
        ]
        
        return Media(css=css, js=js)


# Export commonly used widgets
__all__ = ['PictureWidget', 'SimpleImageWidget'] 