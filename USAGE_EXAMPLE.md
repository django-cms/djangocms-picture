# Usage Examples for Reusable PictureField

## Basic Usage in Custom Models

```python
from django.db import models
from djangocms_picture.fields import PictureField

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # Basic picture field with default settings
    featured_image = PictureField(
        help_text="Main image for the blog post"
    )
    
    # Picture field with custom configuration
    hero_image = PictureField(
        responsive=True,
        breakpoints=[480, 768, 1024, 1200],
        allow_links=True,
        alignment_choices=[
            ('left', 'Left'),
            ('center', 'Center'),
            ('right', 'Right'),
            ('full', 'Full Width'),
        ],
        max_size=5 * 1024 * 1024,  # 5MB max
        help_text="Hero image with responsive breakpoints"
    )
    
    # Simple image field without full picture configuration
    thumbnail = PictureField(
        responsive=False,
        allow_links=False,
        help_text="Simple thumbnail image"
    )

class ProductCatalog(models.Model):
    name = models.CharField(max_length=100)
    
    # Picture field with specific backend
    product_image = PictureField(
        backend='filer',  # Use filer backend specifically
        responsive=True,
        formats=['webp', 'jpeg'],  # Support specific formats
        help_text="Product image using filer backend"
    )
```

## Usage in Forms

```python
from django import forms
from djangocms_picture.fields import PictureFormField

class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = '__all__'
    
    # The form field is automatically generated from the model field
    # But you can override it with custom settings
    featured_image = PictureFormField(
        required=False,
        help_text="Upload or select a featured image"
    )

class CustomImageForm(forms.Form):
    # Use PictureFormField in a regular form
    banner_image = PictureFormField(
        responsive=True,
        breakpoints=[576, 768, 992, 1200],
        allow_links=True,
        max_size=10 * 1024 * 1024,  # 10MB max
        help_text="Banner image for the page"
    )
    
    # Simple image selection
    logo = PictureFormField(
        responsive=False,
        allow_links=False,
        alignment_choices=[('center', 'Center')],
        help_text="Company logo"
    )
```

## Accessing Picture Data

```python
# Get a blog post
blog_post = BlogPost.objects.get(id=1)

# Access the picture data
featured_image = blog_post.featured_image
if featured_image:
    print(f"Image reference: {featured_image.image_reference}")
    print(f"Alt text: {featured_image.alt_text}")
    print(f"Width: {featured_image.width}")
    print(f"Height: {featured_image.height}")
    print(f"Responsive: {featured_image.responsive}")
    print(f"Alignment: {featured_image.alignment}")
    
    # Get image URL using backend
    from djangocms_picture.backends import backend_registry
    backend = backend_registry.get_backend('filer')
    
    # Get original image URL
    original_url = backend.get_image_url(featured_image.image_reference)
    
    # Get resized image URL
    resized_url = backend.get_image_url(
        featured_image.image_reference,
        size_options={'size': (300, 200), 'crop': True}
    )
    
    # Get responsive srcset data
    srcset_data = backend.get_srcset_data(
        featured_image.image_reference,
        breakpoints=[576, 768, 992, 1200],
        crop=True
    )
```

## Template Usage

```html
<!-- In your template -->
{% load picture_tags %}

<!-- Render responsive picture -->
{% picture blog_post.featured_image %}

<!-- Render with custom options -->
{% picture blog_post.hero_image crop=True quality=85 %}

<!-- Render with specific size -->
{% picture blog_post.thumbnail width=150 height=150 %}

<!-- Manual template rendering -->
{% if blog_post.featured_image %}
    <figure class="featured-image {{ blog_post.featured_image.alignment }}">
        <img src="{{ blog_post.featured_image.image_url }}" 
             alt="{{ blog_post.featured_image.alt_text }}"
             width="{{ blog_post.featured_image.width }}"
             height="{{ blog_post.featured_image.height }}">
        {% if blog_post.featured_image.caption %}
            <figcaption>{{ blog_post.featured_image.caption }}</figcaption>
        {% endif %}
    </figure>
{% endif %}
```

## Admin Integration

```python
from django.contrib import admin
from .models import BlogPost

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'has_featured_image']
    
    def has_featured_image(self, obj):
        return bool(obj.featured_image)
    has_featured_image.boolean = True
    has_featured_image.short_description = 'Has Featured Image'
    
    # The PictureField automatically provides a rich widget in the admin
```

## Settings Configuration

```python
# settings.py

# Configure default backend
DJANGOCMS_PICTURE_DEFAULT_BACKEND = 'filer'

# Configure available backends
DJANGOCMS_PICTURE_BACKENDS = {
    'filer': 'djangocms_picture.backends.filer.FilerImageBackend',
    'native': 'djangocms_picture.backends.native.NativeImageBackend',
}

# Configure default responsive breakpoints
DJANGOCMS_PICTURE_RESPONSIVE_BREAKPOINTS = [576, 768, 992, 1200]

# Configure default image formats
DJANGOCMS_PICTURE_FORMATS = ['webp', 'jpeg', 'png']
```

## Working with Different Backends

```python
# Using different backends for different purposes
class MediaAsset(models.Model):
    name = models.CharField(max_length=100)
    
    # Use filer for managed images
    managed_image = PictureField(
        backend='filer',
        help_text="Managed image using filer"
    )
    
    # Use native Django for simple images
    simple_image = PictureField(
        backend='native',
        help_text="Simple image using native Django"
    )
    
    # Allow external images
    external_image = PictureField(
        backend='external',
        help_text="External image URL"
    )
```

This reusable PictureField system provides a comprehensive, flexible way to handle images in Django applications while maintaining compatibility with existing djangocms-picture functionality. 