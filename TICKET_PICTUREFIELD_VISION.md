# Feature Request: Reusable PictureField and PictureFormField Implementation

## Overview

This ticket outlines the implementation of reusable `PictureField` and `PictureFormField` components that can be used both within the Picture plugin and by external developers in their custom models and forms. This aligns with the long-term vision of making djangocms-picture the central hub for all picture-related functionality in the Django CMS ecosystem.

## Background

Currently, the Picture plugin functionality is tightly coupled to the CMS plugin system. The goal is to extract and generalize the core image handling capabilities into reusable components that can:

1. Be used in custom Django models outside of CMS plugins
2. Support multiple image backends (django-filer, native Django ImageField, future DAM systems)
3. Provide a consistent API for image configuration across different use cases
4. Enable other plugins (like djangocms-frontend) to depend on djangocms-picture for image handling

## Detailed Requirements

### 1. PictureField (Model Field)

**Purpose**: A reusable model field that can be used in any Django model to handle images with the same capabilities as the Picture plugin.

**Key Features**:
- Support for multiple image backends:
  - `FilerImageBackend` (current default using django-filer)
  - `NativeImageBackend` (using Django's ImageField)
  - Extensible architecture for future backends (DAM systems, cloud storage, etc.)
- Configurable image processing options:
  - Responsive image generation with srcset
  - Custom thumbnail sizes and cropping
  - Automatic scaling and optimization
  - WebP/AVIF format support
- Link functionality (internal pages, external URLs)
- Accessibility features (alt text, captions)
- Alignment and styling options

**API Design**:
```python
from djangocms_picture.fields import PictureField

class Article(models.Model):
    title = models.CharField(max_length=200)
    featured_image = PictureField(
        backend='filer',  # or 'native', 'custom'
        responsive=True,
        breakpoints=[576, 768, 992, 1200],
        formats=['webp', 'jpeg'],
        allow_links=True,
        alignment_choices=['left', 'center', 'right'],
        blank=True, null=True
    )
```

### 2. PictureFormField (Form Field)

**Purpose**: A form field that provides a comprehensive interface for configuring all image parameters.

**Key Features**:
- Image selection/upload interface
- Responsive image configuration (Yes/No toggle)
- Size and crop area settings (cover, contain, custom)
- Custom alt text input
- Link configuration (internal/external)
- Alignment selection
- Live preview of settings
- Validation for image dimensions, file types, sizes

**Configuration Options**:
- Image source (upload, filer selection, external URL)
- Responsiveness settings
- Dimensions (width, height, aspect ratio)
- Cropping options (automatic, manual, subject location aware)
- Optimization settings (quality, format conversion)
- Link settings (page, URL, target, attributes)
- Accessibility (alt text, caption, description)
- Styling (alignment, CSS classes, custom attributes)

### 3. PictureWidget (Form Widget)

**Purpose**: A modern, user-friendly widget for the PictureFormField.

**Key Features**:
- Tabbed interface organizing different configuration aspects:
  - **Image**: Selection, upload, external URL
  - **Display**: Dimensions, cropping, responsive settings
  - **Links**: Page links, external URLs, targets
  - **Accessibility**: Alt text, captions, descriptions
  - **Advanced**: CSS classes, custom attributes, alignment
- Live preview showing how the image will appear
- Drag-and-drop upload support
- Integration with django-filer's file picker
- Responsive design that works on mobile and desktop
- Accessibility compliant (WCAG 2.1)

### 4. Backend Abstraction System

**Purpose**: Pluggable backend system to support different image storage and processing solutions.

**Backend Interface**:
```python
class ImageBackend:
    def save_image(self, image_file, instance, field_name): ...
    def get_image_url(self, image_reference, size_options): ...
    def get_srcset_data(self, image_reference, breakpoints): ...
    def delete_image(self, image_reference): ...
    def get_image_info(self, image_reference): ...
```

**Included Backends**:
- **FilerImageBackend**: Current integration with django-filer
- **NativeImageBackend**: Uses Django's ImageField with easy-thumbnails
- **ExternalImageBackend**: For external image URLs

### 5. Configuration System

**Settings**:
```python
# Django settings.py
DJANGOCMS_PICTURE_BACKENDS = {
    'filer': 'djangocms_picture.backends.FilerImageBackend',
    'native': 'djangocms_picture.backends.NativeImageBackend',
    'external': 'djangocms_picture.backends.ExternalImageBackend',
}

DJANGOCMS_PICTURE_DEFAULT_BACKEND = 'filer'

DJANGOCMS_PICTURE_RESPONSIVE_BREAKPOINTS = [576, 768, 992, 1200]
DJANGOCMS_PICTURE_DEFAULT_FORMATS = ['webp', 'jpeg']
DJANGOCMS_PICTURE_QUALITY_SETTINGS = {
    'webp': 85,
    'jpeg': 90,
    'png': 95,
}
```

## Implementation Plan

### Phase 1: Core Architecture
1. Create backend abstraction system
2. Implement FilerImageBackend (maintain current functionality)
3. Design PictureField model field
4. Create basic PictureFormField

### Phase 2: Enhanced Features
1. Implement NativeImageBackend
2. Create modern PictureWidget with tabbed interface
3. Add responsive image generation
4. Implement format conversion (WebP, AVIF)

### Phase 3: Integration and Migration
1. Update Picture plugin to use new fields
2. Create migration path for existing installations
3. Add comprehensive test suite
4. Create documentation and examples

### Phase 4: Advanced Features
1. Add support for art direction (different images for different breakpoints)
2. Implement lazy loading options
3. Add image optimization pipeline
4. Create CLI tools for batch processing

## Benefits

### For Plugin Users
- More consistent and powerful image handling
- Better performance with modern formats and responsive images
- Improved accessibility features
- Enhanced user experience with better admin interface

### For Developers
- Reusable components for custom models
- Clean API for image handling in any Django project
- Extensible backend system for custom storage solutions
- Better separation of concerns

### For the Ecosystem
- Central hub for image functionality
- Reduced code duplication across plugins
- Standardized approach to image handling in Django CMS
- Foundation for future enhancements

## Migration Strategy

### Backward Compatibility
- Existing Picture plugin instances continue to work unchanged
- Current API remains available during transition period
- Migration commands to update existing data

### Upgrade Path
1. Install updated djangocms-picture
2. Run migration commands to update database schema
3. Optionally migrate to new field types for enhanced features
4. Update custom code to use new APIs when ready

## Success Metrics

1. **Adoption**: Other djangocms packages start using PictureField
2. **Performance**: Improved page load times with responsive images
3. **Developer Experience**: Positive feedback on API usability
4. **Extensibility**: Community creates additional backends
5. **Maintenance**: Reduced code duplication across CMS plugins

## Related Issues and Discussions

- Discussion #153: djangocms-picture vision and roadmap
- Need for reusable image fields in custom models
- Request for multiple image backend support
- Demand for modern responsive image handling

## Technical Considerations

### Database Schema
- New fields may require migrations for existing installations
- Backend selection stored as configuration, not in database
- Maintain compatibility with existing filer integration

### Performance
- Lazy loading of image processing
- Efficient srcset generation
- Caching strategies for thumbnails and responsive variants

### Security
- Validate image uploads and processing
- Sanitize user input for attributes and links
- Secure handling of external image URLs

### Testing
- Unit tests for all field types and backends
- Integration tests with different Django/CMS versions
- Performance tests for image processing
- UI tests for admin interface

This implementation will establish djangocms-picture as the definitive solution for image handling in Django CMS and beyond, providing a solid foundation for future enhancements and ecosystem growth. 