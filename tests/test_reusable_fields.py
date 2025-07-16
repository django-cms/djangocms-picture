"""
Tests for the reusable PictureField functionality.
"""
import json

from django.core.exceptions import ValidationError
from django.db import models
from django.forms import ModelForm
from django.test import TestCase

from djangocms_picture.backends import backend_registry
from djangocms_picture.fields import PictureData, PictureField
from djangocms_picture.fields.forms import PictureFormField


class PictureTestModel(models.Model):
    """Test model with PictureField."""
    name = models.CharField(max_length=100)
    picture = PictureField()

    class Meta:
        app_label = 'test_app'


class PictureTestModelForm(ModelForm):
    """Test form for PictureTestModel."""
    class Meta:
        model = PictureTestModel
        fields = '__all__'


class PictureDataTestCase(TestCase):
    """Test PictureData class."""

    def test_init_with_dict(self):
        """Test initialization with dict."""
        data = {'width': 800, 'height': 600, 'alt_text': 'Test image'}
        picture_data = PictureData(data)

        self.assertEqual(picture_data.width, 800)
        self.assertEqual(picture_data.height, 600)
        self.assertEqual(picture_data.alt_text, 'Test image')

    def test_init_with_json(self):
        """Test initialization with JSON string."""
        json_data = '{"width": 800, "height": 600, "alt_text": "Test image"}'
        picture_data = PictureData(json_data)

        self.assertEqual(picture_data.width, 800)
        self.assertEqual(picture_data.height, 600)
        self.assertEqual(picture_data.alt_text, 'Test image')

    def test_init_with_invalid_json(self):
        """Test initialization with invalid JSON."""
        picture_data = PictureData('invalid json')
        self.assertEqual(picture_data.width, None)
        self.assertEqual(picture_data.alt_text, '')

    def test_init_empty(self):
        """Test initialization with empty data."""
        picture_data = PictureData()
        self.assertEqual(picture_data.width, None)
        self.assertEqual(picture_data.height, None)
        self.assertEqual(picture_data.alt_text, '')
        self.assertEqual(picture_data.responsive, True)

    def test_property_setters(self):
        """Test property setters."""
        picture_data = PictureData()

        # Test width/height
        picture_data.width = 1024
        picture_data.height = 768
        self.assertEqual(picture_data.width, 1024)
        self.assertEqual(picture_data.height, 768)

        # Test string properties
        picture_data.alt_text = 'Alt text'
        picture_data.caption = 'Caption'
        picture_data.alignment = 'center'
        self.assertEqual(picture_data.alt_text, 'Alt text')
        self.assertEqual(picture_data.caption, 'Caption')
        self.assertEqual(picture_data.alignment, 'center')

        # Test boolean properties
        picture_data.responsive = False
        picture_data.crop = True
        self.assertEqual(picture_data.responsive, False)
        self.assertEqual(picture_data.crop, True)

    def test_to_json(self):
        """Test JSON serialization."""
        picture_data = PictureData()
        picture_data.width = 800
        picture_data.height = 600
        picture_data.alt_text = 'Test'

        json_str = picture_data.to_json()
        parsed = json.loads(json_str)

        self.assertEqual(parsed['width'], 800)
        self.assertEqual(parsed['height'], 600)
        self.assertEqual(parsed['alt_text'], 'Test')

    def test_bool_conversion(self):
        """Test boolean conversion."""
        # Empty picture data
        picture_data = PictureData()
        self.assertFalse(picture_data)

        # With image reference
        picture_data.image_reference = 'test_image.jpg'
        self.assertTrue(picture_data)

        # With external URL
        picture_data.image_reference = None
        picture_data.external_url = 'https://example.com/image.jpg'
        self.assertTrue(picture_data)

    def test_str_representation(self):
        """Test string representation."""
        picture_data = PictureData()
        self.assertEqual(str(picture_data), 'Empty Picture')

        picture_data.external_url = 'https://example.com/image.jpg'
        self.assertEqual(str(picture_data), 'External: https://example.com/image.jpg')

        picture_data.external_url = ''
        picture_data.image_reference = 'test_image.jpg'
        self.assertEqual(str(picture_data), 'Image: test_image.jpg')


class PictureFieldTestCase(TestCase):
    """Test PictureField model field."""

    def test_field_creation(self):
        """Test field creation with default options."""
        field = PictureField()

        self.assertEqual(field.responsive, True)
        self.assertEqual(field.breakpoints, [576, 768, 992, 1200])
        self.assertEqual(field.formats, ['webp', 'jpeg', 'png'])
        self.assertEqual(field.allow_links, True)
        self.assertIsNone(field.backend_name)

    def test_field_creation_with_options(self):
        """Test field creation with custom options."""
        field = PictureField(
            backend='filer',
            responsive=False,
            breakpoints=[768, 1024],
            formats=['jpeg', 'png'],
            allow_links=False,
            max_size=1024*1024
        )

        self.assertEqual(field.backend_name, 'filer')
        self.assertEqual(field.responsive, False)
        self.assertEqual(field.breakpoints, [768, 1024])
        self.assertEqual(field.formats, ['jpeg', 'png'])
        self.assertEqual(field.allow_links, False)
        self.assertEqual(field.max_size, 1024*1024)

    def test_to_python(self):
        """Test conversion to Python object."""
        field = PictureField()

        # Test with None
        self.assertIsNone(field.to_python(None))

        # Test with PictureData
        picture_data = PictureData({'width': 800})
        result = field.to_python(picture_data)
        self.assertEqual(result, picture_data)

        # Test with dict
        data = {'width': 800, 'height': 600}
        result = field.to_python(data)
        self.assertIsInstance(result, PictureData)
        self.assertEqual(result.width, 800)
        self.assertEqual(result.height, 600)

    def test_from_db_value(self):
        """Test conversion from database value."""
        field = PictureField()

        # Test with None
        result = field.from_db_value(None, None, None)
        self.assertIsNone(result)

        # Test with JSON string
        json_data = '{"width": 800, "height": 600}'
        result = field.from_db_value(json_data, None, None)
        self.assertIsInstance(result, PictureData)
        self.assertEqual(result.width, 800)
        self.assertEqual(result.height, 600)

    def test_get_prep_value(self):
        """Test conversion to database value."""
        field = PictureField()

        # Test with None
        result = field.get_prep_value(None)
        self.assertIsNone(result)

        # Test with PictureData
        picture_data = PictureData({'width': 800, 'height': 600})
        result = field.get_prep_value(picture_data)
        self.assertIsInstance(result, str)
        parsed = json.loads(result)
        self.assertEqual(parsed['width'], 800)
        self.assertEqual(parsed['height'], 600)

    def test_validate(self):
        """Test field validation."""
        field = PictureField()

        # Test with valid data
        picture_data = PictureData()
        picture_data.image_reference = 'test.jpg'
        field.validate(picture_data, None)  # Should not raise

        # Test with invalid data (has data but no image or URL)
        picture_data = PictureData()
        picture_data.width = 800  # Add some data to make it truthy
        with self.assertRaises(ValidationError):
            field.validate(picture_data, None)

        # Test with conflicting links
        picture_data = PictureData()
        picture_data.image_reference = 'test.jpg'
        picture_data.link_url = 'https://example.com'
        picture_data.link_page_id = 123
        with self.assertRaises(ValidationError):
            field.validate(picture_data, None)

    def test_deconstruct(self):
        """Test field deconstruction for migrations."""
        field = PictureField(
            backend='filer',
            responsive=False,
            breakpoints=[768, 1024],
            max_size=1024*1024
        )

        name, path, args, kwargs = field.deconstruct()

        self.assertEqual(kwargs['backend'], 'filer')
        self.assertEqual(kwargs['responsive'], False)
        self.assertEqual(kwargs['breakpoints'], [768, 1024])
        self.assertEqual(kwargs['max_size'], 1024*1024)


class PictureFormFieldTestCase(TestCase):
    """Test PictureFormField form field."""

    def test_field_creation(self):
        """Test form field creation."""
        field = PictureFormField()

        self.assertEqual(field.responsive, True)
        self.assertEqual(field.breakpoints, [576, 768, 992, 1200])
        self.assertEqual(field.allow_links, True)
        self.assertIsNone(field.backend_name)

    def test_to_python(self):
        """Test conversion to Python object."""
        field = PictureFormField()

        # Test with empty value
        self.assertIsNone(field.to_python(''))
        self.assertIsNone(field.to_python(None))

        # Test with PictureData
        picture_data = PictureData({'width': 800})
        result = field.to_python(picture_data)
        self.assertEqual(result, picture_data)

        # Test with JSON string
        json_data = '{"width": 800, "height": 600}'
        result = field.to_python(json_data)
        self.assertIsInstance(result, PictureData)
        self.assertEqual(result.width, 800)

        # Test with dict
        data = {'width': 800, 'height': 600}
        result = field.to_python(data)
        self.assertIsInstance(result, PictureData)
        self.assertEqual(result.width, 800)

    def test_validate(self):
        """Test form field validation."""
        field = PictureFormField(required=True)

        # Test with valid data
        picture_data = PictureData()
        picture_data.image_reference = 'test.jpg'
        field.validate(picture_data)  # Should not raise

        # Test with required field and no image
        picture_data = PictureData()
        with self.assertRaises(ValidationError):
            field.validate(picture_data)

        # Test with conflicting links
        picture_data = PictureData()
        picture_data.image_reference = 'test.jpg'
        picture_data.link_url = 'https://example.com'
        picture_data.link_page_id = 123
        with self.assertRaises(ValidationError):
            field.validate(picture_data)

        # Test with invalid dimensions
        picture_data = PictureData()
        picture_data.image_reference = 'test.jpg'
        picture_data.width = -100
        with self.assertRaises(ValidationError):
            field.validate(picture_data)


class BackendRegistryTestCase(TestCase):
    """Test backend registry functionality."""

    def test_get_backend(self):
        """Test getting backend by name."""
        # Test getting filer backend
        backend = backend_registry.get_backend('filer')
        self.assertIsNotNone(backend)

        # Test getting non-existent backend
        with self.assertRaises(Exception):
            backend_registry.get_backend('non_existent')

    def test_get_available_backends(self):
        """Test getting available backends."""
        backends = backend_registry.get_available_backends()
        self.assertIn('filer', backends)


class IntegrationTestCase(TestCase):
    """Test integration between field, form, and backend."""

    def test_model_form_integration(self):
        """Test that model form works with PictureField."""
        # Create form with valid picture data (with image reference)
        form_data = {
            'name': 'Test Model',
            'picture': '{"width": 800, "height": 600, "alt_text": "Test", "image_reference": "test.jpg"}'
        }

        form = PictureTestModelForm(data=form_data)

        # Form should be valid
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

        # Check that picture field is properly converted
        picture_data = form.cleaned_data['picture']
        self.assertIsInstance(picture_data, PictureData)
        self.assertEqual(picture_data.width, 800)
        self.assertEqual(picture_data.height, 600)
        self.assertEqual(picture_data.alt_text, 'Test')

    def test_field_widget_integration(self):
        """Test that field provides proper widget."""
        field = PictureField()
        form_field = field.formfield()

        self.assertIsInstance(form_field, PictureFormField)
        self.assertEqual(form_field.responsive, True)
        self.assertEqual(form_field.allow_links, True)

        # Test widget is attached
        self.assertIsNotNone(form_field.widget)
