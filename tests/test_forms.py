"""
Tests for djangocms-picture form fields.
"""
import json
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from djangocms_picture.fields import PictureData
from djangocms_picture.fields.forms import PictureFormField, ImageSelectionField


class PictureFormFieldTestCase(TestCase):
    """Test PictureFormField functionality."""

    def setUp(self):
        """Set up test environment."""
        self.field = PictureFormField()
        self.test_image_file = SimpleUploadedFile(
            "test.jpg",
            b"fake image data",
            content_type="image/jpeg"
        )

    def test_init_defaults(self):
        """Test field initialization with defaults."""
        field = PictureFormField()
        
        self.assertIsNone(field.backend_name)
        self.assertTrue(field.responsive)
        self.assertEqual(field.breakpoints, [576, 768, 992, 1200])
        self.assertEqual(field.formats, ['webp', 'jpeg', 'png'])
        self.assertTrue(field.allow_links)
        self.assertEqual(len(field.alignment_choices), 3)
        self.assertIsNone(field.max_size)
        self.assertFalse(field.required)

    def test_init_custom_options(self):
        """Test field initialization with custom options."""
        field = PictureFormField(
            backend='filer',
            responsive=False,
            breakpoints=[768, 992],
            formats=['jpeg', 'png'],
            allow_links=False,
            alignment_choices=[('left', 'Left')],
            max_size=1024*1024,
            required=True
        )
        
        self.assertEqual(field.backend_name, 'filer')
        self.assertFalse(field.responsive)
        self.assertEqual(field.breakpoints, [768, 992])
        self.assertEqual(field.formats, ['jpeg', 'png'])
        self.assertFalse(field.allow_links)
        self.assertEqual(field.alignment_choices, [('left', 'Left')])
        self.assertEqual(field.max_size, 1024*1024)
        self.assertTrue(field.required)

    def test_get_widget(self):
        """Test getting widget."""
        field = PictureFormField(backend='filer', responsive=False)
        
        widget = field._get_widget()
        
        from djangocms_picture.widgets import PictureWidget
        self.assertIsInstance(widget, PictureWidget)
        self.assertEqual(widget.backend_name, 'filer')
        self.assertFalse(widget.responsive)

    def test_get_backend(self):
        """Test getting backend."""
        field = PictureFormField(backend='filer')
        
        with patch('djangocms_picture.fields.forms.backend_registry.get_backend') as mock_get:
            mock_backend = Mock()
            mock_get.return_value = mock_backend
            
            result = field.get_backend()
            
            self.assertEqual(result, mock_backend)
            mock_get.assert_called_once_with('filer')

    def test_to_python_none(self):
        """Test converting None value."""
        result = self.field.to_python(None)
        self.assertIsNone(result)

    def test_to_python_empty_string(self):
        """Test converting empty string."""
        result = self.field.to_python('')
        self.assertIsNone(result)

    def test_to_python_whitespace_string(self):
        """Test converting whitespace-only string."""
        result = self.field.to_python('   ')
        self.assertIsNone(result)

    def test_to_python_picture_data(self):
        """Test converting PictureData object."""
        picture_data = PictureData({'width': 800})
        
        result = self.field.to_python(picture_data)
        
        self.assertEqual(result, picture_data)

    def test_to_python_json_string(self):
        """Test converting JSON string."""
        json_data = '{"width": 800, "height": 600}'
        
        result = self.field.to_python(json_data)
        
        self.assertIsInstance(result, PictureData)
        self.assertEqual(result.width, 800)
        self.assertEqual(result.height, 600)

    def test_to_python_invalid_json_string(self):
        """Test converting invalid JSON string."""
        invalid_json = 'not json'
        
        result = self.field.to_python(invalid_json)
        
        self.assertIsInstance(result, PictureData)
        self.assertEqual(result.image_reference, 'not json')

    def test_to_python_dict(self):
        """Test converting dictionary."""
        data = {'width': 800, 'height': 600}
        
        result = self.field.to_python(data)
        
        self.assertIsInstance(result, PictureData)
        self.assertEqual(result.width, 800)
        self.assertEqual(result.height, 600)

    def test_to_python_file_upload_valid(self):
        """Test converting file upload with valid image."""
        field = PictureFormField(max_size=1024*1024)
        
        with patch.object(field, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_backend.validate_image = Mock()  # No exception = valid
            mock_get_backend.return_value = mock_backend
            
            result = field.to_python(self.test_image_file)
            
            self.assertIsInstance(result, PictureData)
            self.assertEqual(result.data['uploaded_file'], self.test_image_file)
            mock_backend.validate_image.assert_called_once_with(
                self.test_image_file, 
                max_size=1024*1024
            )

    def test_to_python_file_upload_invalid(self):
        """Test converting file upload with invalid image."""
        with patch.object(self.field, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_backend.validate_image.side_effect = ValidationError("Invalid image")
            mock_get_backend.return_value = mock_backend
            
            with self.assertRaises(ValidationError):
                self.field.to_python(self.test_image_file)

    def test_to_python_unsupported_type(self):
        """Test converting unsupported type."""
        result = self.field.to_python(123)
        self.assertIsNone(result)

    def test_validate_required_field_empty(self):
        """Test validation of required field with empty value."""
        field = PictureFormField(required=True)
        
        with self.assertRaises(ValidationError):
            field.validate(None)
        
        with self.assertRaises(ValidationError):
            field.validate(PictureData())  # Empty PictureData

    def test_validate_required_field_with_value(self):
        """Test validation of required field with value."""
        field = PictureFormField(required=True)
        picture_data = PictureData()
        picture_data.image_reference = 'test.jpg'
        
        # Should not raise any exception
        field.validate(picture_data)

    def test_validate_conflicting_links(self):
        """Test validation with conflicting link configuration."""
        picture_data = PictureData()
        picture_data.image_reference = 'test.jpg'  # Make it truthy
        picture_data.link_url = 'http://example.com'
        picture_data.link_page_id = 123
        
        with self.assertRaises(ValidationError) as cm:
            self.field.validate(picture_data)
        
        self.assertIn('Cannot have both external URL and page link', str(cm.exception))

    def test_validate_negative_width(self):
        """Test validation with negative width."""
        picture_data = PictureData()
        picture_data.image_reference = 'test.jpg'  # Make it truthy
        picture_data.width = -100
        
        with self.assertRaises(ValidationError) as cm:
            self.field.validate(picture_data)
        
        self.assertIn('Width must be positive', str(cm.exception))

    def test_validate_zero_width(self):
        """Test validation with zero width."""
        picture_data = PictureData()
        picture_data.image_reference = 'test.jpg'  # Make it truthy
        picture_data.width = 0
        
        with self.assertRaises(ValidationError) as cm:
            self.field.validate(picture_data)
        
        self.assertIn('Width must be positive', str(cm.exception))

    def test_validate_negative_height(self):
        """Test validation with negative height."""
        picture_data = PictureData()
        picture_data.image_reference = 'test.jpg'  # Make it truthy
        picture_data.height = -100
        
        with self.assertRaises(ValidationError) as cm:
            self.field.validate(picture_data)
        
        self.assertIn('Height must be positive', str(cm.exception))

    def test_validate_zero_height(self):
        """Test validation with zero height."""
        picture_data = PictureData()
        picture_data.image_reference = 'test.jpg'  # Make it truthy
        picture_data.height = 0
        
        with self.assertRaises(ValidationError) as cm:
            self.field.validate(picture_data)
        
        self.assertIn('Height must be positive', str(cm.exception))

    def test_validate_positive_dimensions(self):
        """Test validation with positive dimensions."""
        picture_data = PictureData()
        picture_data.width = 800
        picture_data.height = 600
        
        # Should not raise any exception
        self.field.validate(picture_data)

    def test_validate_none_dimensions(self):
        """Test validation with None dimensions."""
        picture_data = PictureData()
        picture_data.width = None
        picture_data.height = None
        
        # Should not raise any exception
        self.field.validate(picture_data)

    def test_validate_not_picture_data(self):
        """Test validation with non-PictureData value."""
        # Should not raise any exception for non-PictureData values
        self.field.validate("some string")
        self.field.validate(123)
        self.field.validate({'key': 'value'})

    def test_clean_valid_data(self):
        """Test cleaning valid data."""
        json_data = '{"width": 800}'
        
        result = self.field.clean(json_data)
        
        self.assertIsInstance(result, PictureData)
        self.assertEqual(result.width, 800)

    def test_clean_invalid_data(self):
        """Test cleaning invalid data."""
        field = PictureFormField(required=True)
        
        with self.assertRaises(ValidationError):
            field.clean(None)

    def test_clean_with_validation_error(self):
        """Test cleaning data that fails validation."""
        picture_data = PictureData()
        picture_data.image_reference = 'test.jpg'  # Make it truthy
        picture_data.width = -100
        
        with self.assertRaises(ValidationError):
            self.field.clean(picture_data)


class ImageSelectionFieldTestCase(TestCase):
    """Test ImageSelectionField functionality."""

    def setUp(self):
        """Set up test environment."""
        self.field = ImageSelectionField()
        self.test_image_file = SimpleUploadedFile(
            "test.jpg",
            b"fake image data",
            content_type="image/jpeg"
        )

    def test_init_defaults(self):
        """Test field initialization with defaults."""
        field = ImageSelectionField()
        
        self.assertIsNone(field.backend_name)
        self.assertFalse(field.required)

    def test_init_custom_backend(self):
        """Test field initialization with custom backend."""
        field = ImageSelectionField(backend='filer', required=True)
        
        self.assertEqual(field.backend_name, 'filer')
        self.assertTrue(field.required)

    def test_get_backend(self):
        """Test getting backend."""
        field = ImageSelectionField(backend='filer')
        
        with patch('djangocms_picture.fields.forms.backend_registry.get_backend') as mock_get:
            mock_backend = Mock()
            mock_get.return_value = mock_backend
            
            result = field.get_backend()
            
            self.assertEqual(result, mock_backend)
            mock_get.assert_called_once_with('filer')

    def test_to_python_empty(self):
        """Test converting empty value."""
        result = self.field.to_python(None)
        self.assertIsNone(result)
        
        result = self.field.to_python('')
        self.assertIsNone(result)

    def test_to_python_file_upload(self):
        """Test converting file upload."""
        with patch.object(self.field, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_get_backend.return_value = mock_backend
            
            result = self.field.to_python(self.test_image_file)
            
            self.assertEqual(result, self.test_image_file)

    def test_to_python_string(self):
        """Test converting string value."""
        with patch.object(self.field, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_get_backend.return_value = mock_backend
            
            result = self.field.to_python('image_reference')
            
            self.assertEqual(result, 'image_reference')

    def test_to_python_other_value(self):
        """Test converting other value types."""
        with patch.object(self.field, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_get_backend.return_value = mock_backend
            
            test_obj = {'key': 'value'}
            result = self.field.to_python(test_obj)
            
            self.assertEqual(result, test_obj)

    def test_validate_file_upload_valid(self):
        """Test validation of valid file upload."""
        with patch.object(self.field, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_backend.validate_image = Mock()  # No exception = valid
            mock_get_backend.return_value = mock_backend
            
            # Should not raise any exception
            self.field.validate(self.test_image_file)
            
            mock_backend.validate_image.assert_called_once_with(self.test_image_file)

    def test_validate_file_upload_invalid(self):
        """Test validation of invalid file upload."""
        with patch.object(self.field, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_backend.validate_image.side_effect = ValidationError("Invalid image")
            mock_get_backend.return_value = mock_backend
            
            with self.assertRaises(ValidationError):
                self.field.validate(self.test_image_file)

    def test_validate_non_file_value(self):
        """Test validation of non-file value."""
        # Should not raise any exception for non-file values
        self.field.validate('image_reference')
        self.field.validate(None)

    def test_validate_required_field(self):
        """Test validation of required field."""
        field = ImageSelectionField(required=True)
        
        with patch('django.forms.Field.validate') as mock_parent_validate:
            field.validate('some_value')
            
            # Should call parent validate method
            mock_parent_validate.assert_called_once_with('some_value')


class FormsExportsTestCase(TestCase):
    """Test forms module exports."""

    def test_all_exports(self):
        """Test that __all__ contains expected fields."""
        from djangocms_picture.fields.forms import __all__
        
        expected = ['PictureFormField', 'ImageSelectionField']
        self.assertEqual(__all__, expected) 