"""
Tests for djangocms-picture backends.
"""
import io
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from filer.models import Image as FilerImage

from djangocms_picture.backends.filer import FilerImageBackend
from djangocms_picture.backends import ImageBackend, BackendRegistry, backend_registry, _register_default_backends


class ImageBackendTestCase(TestCase):
    """Test base ImageBackend functionality."""

    def test_base_backend_abstract_methods(self):
        """Test that base backend methods raise NotImplementedError."""
        backend = ImageBackend()
        
        # All methods should raise NotImplementedError (they're abstract)
        with self.assertRaises(NotImplementedError):
            backend.save_image(None, None, None)
        
        with self.assertRaises(NotImplementedError):
            backend.get_image_url(None)
        
        with self.assertRaises(NotImplementedError):
            backend.get_srcset_data(None, [])
        
        with self.assertRaises(NotImplementedError):
            backend.delete_image(None)
        
        with self.assertRaises(NotImplementedError):
            backend.get_image_info(None)
        
        # validate_image should not raise (it has a default implementation)
        backend.validate_image(None)


class BackendRegistryTestCase(TestCase):
    """Test BackendRegistry functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create a fresh registry for each test
        self.registry = BackendRegistry()

    def test_init(self):
        """Test registry initialization."""
        registry = BackendRegistry()
        
        self.assertEqual(registry._backends, {})
        self.assertFalse(registry._loaded)

    def test_load_backends_default(self):
        """Test loading default backends when no settings are configured."""
        with patch('djangocms_picture.backends._register_default_backends') as mock_register:
            with patch('django.conf.settings.DJANGOCMS_PICTURE_BACKENDS', {}, create=True):
                self.registry._load_backends()
                
                mock_register.assert_called_once()
                self.assertTrue(self.registry._loaded)

    @override_settings(DJANGOCMS_PICTURE_BACKENDS={
        'test_backend': 'tests.test_backends.FilerImageBackend'
    })
    def test_load_backends_from_settings_success(self):
        """Test loading backends from Django settings successfully."""
        self.registry._load_backends()
        
        self.assertTrue(self.registry._loaded)
        self.assertIn('test_backend', self.registry._backends)
        self.assertEqual(self.registry._backends['test_backend'], FilerImageBackend)

    @override_settings(DJANGOCMS_PICTURE_BACKENDS={
        'invalid_backend': 'non.existent.Backend'
    })
    def test_load_backends_from_settings_import_error(self):
        """Test loading backends with import error."""
        with patch('logging.warning') as mock_warning:
            self.registry._load_backends()
            
            # Should log warning instead of raising error
            mock_warning.assert_called_once()
            self.assertTrue(self.registry._loaded)
            self.assertNotIn('invalid_backend', self.registry._backends)

    def test_load_backends_only_once(self):
        """Test that backends are only loaded once."""
        with patch('django.conf.settings.DJANGOCMS_PICTURE_BACKENDS', {}, create=True):
            with patch('djangocms_picture.backends._register_default_backends') as mock_register:
                # First call should load
                self.registry._load_backends()
                mock_register.assert_called_once()
                
                # Second call should not load again
                self.registry._load_backends()
                mock_register.assert_called_once()  # Still only once

    def test_get_backend_default(self):
        """Test getting default backend."""
        with patch.object(self.registry, '_load_backends'):
            self.registry._backends = {'filer': FilerImageBackend}
            
            with override_settings(DJANGOCMS_PICTURE_DEFAULT_BACKEND='filer'):
                backend = self.registry.get_backend()
                
                self.assertIsInstance(backend, FilerImageBackend)

    def test_get_backend_by_name(self):
        """Test getting backend by specific name."""
        with patch.object(self.registry, '_load_backends'):
            self.registry._backends = {'test': FilerImageBackend}
            
            backend = self.registry.get_backend('test')
            
            self.assertIsInstance(backend, FilerImageBackend)

    def test_get_backend_not_found(self):
        """Test getting non-existent backend."""
        with patch.object(self.registry, '_load_backends'):
            self.registry._backends = {'filer': FilerImageBackend}
            
            with self.assertRaises(ImproperlyConfigured) as cm:
                self.registry.get_backend('non_existent')
            
            self.assertIn("Backend 'non_existent' not found", str(cm.exception))
            self.assertIn("Available backends: filer", str(cm.exception))

    def test_get_available_backends(self):
        """Test getting list of available backends."""
        with patch.object(self.registry, '_load_backends'):
            self.registry._backends = {
                'filer': FilerImageBackend,
                'test': Mock,
            }
            
            backends = self.registry.get_available_backends()
            
            self.assertEqual(set(backends), {'filer', 'test'})

    def test_get_available_backends_triggers_load(self):
        """Test that get_available_backends triggers loading."""
        with patch.object(self.registry, '_load_backends') as mock_load:
            self.registry._backends = {'test': Mock}
            
            self.registry.get_available_backends()
            
            mock_load.assert_called_once()


class DefaultBackendsTestCase(TestCase):
    """Test default backend registration."""

    def test_register_default_backends_success(self):
        """Test registering default backends successfully."""
        with patch('djangocms_picture.backends.filer.FilerImageBackend', FilerImageBackend):
            _register_default_backends()
            
            # Should have filer backend registered
            self.assertIn('filer', backend_registry._backends)
            self.assertEqual(backend_registry._backends['filer'], FilerImageBackend)
            self.assertTrue(backend_registry._loaded)

    def test_register_default_backends_import_error(self):
        """Test registering default backends with import error."""
        # Create a fresh registry to avoid state pollution
        test_registry = BackendRegistry()
        
        with patch('djangocms_picture.backends.backend_registry', test_registry):
            with patch('djangocms_picture.backends.filer', side_effect=ImportError):
                _register_default_backends()
                
                # Should not have filer backend if import fails
                self.assertNotIn('filer', test_registry._backends)
                self.assertTrue(test_registry._loaded)


class GlobalRegistryTestCase(TestCase):
    """Test global backend registry."""

    def test_global_registry_exists(self):
        """Test that global registry instance exists."""
        from djangocms_picture.backends import backend_registry
        
        self.assertIsInstance(backend_registry, BackendRegistry)

    def test_global_registry_get_backend_filer(self):
        """Test getting filer backend from global registry."""
        # This should work since filer should be available in test environment
        backend = backend_registry.get_backend('filer')
        
        self.assertIsInstance(backend, FilerImageBackend)


class FilerImageBackendTestCase(TestCase):
    """Test FilerImageBackend functionality."""

    def setUp(self):
        """Set up test environment."""
        self.backend = FilerImageBackend()
        self.test_image_data = b'fake image data'
        self.test_image_file = SimpleUploadedFile(
            "test.jpg",
            self.test_image_data,
            content_type="image/jpeg"
        )

    def test_save_image_with_new_file(self):
        """Test saving a new image file."""
        with patch('filer.models.Image.objects.create') as mock_create:
            mock_image = Mock()
            mock_create.return_value = mock_image
            
            result = self.backend.save_image(
                self.test_image_file, 
                instance=None, 
                field_name='test_field'
            )
            
            # The method currently returns the input file if it doesn't have a 'file' attribute
            # Let's test the actual behavior
            self.assertEqual(result, self.test_image_file)

    def test_save_image_with_existing_filer_image(self):
        """Test saving an already existing filer image."""
        mock_filer_image = Mock()
        mock_filer_image.file = Mock()
        
        result = self.backend.save_image(
            mock_filer_image,
            instance=None,
            field_name='test_field'
        )
        
        self.assertEqual(result, mock_filer_image)

    def test_get_image_url_no_image(self):
        """Test getting URL with no image reference."""
        result = self.backend.get_image_url(None)
        self.assertEqual(result, '')

    def test_get_image_url_no_size_options(self):
        """Test getting URL without size options."""
        mock_image = Mock()
        mock_image.url = 'http://example.com/image.jpg'
        
        result = self.backend.get_image_url(mock_image)
        self.assertEqual(result, 'http://example.com/image.jpg')

    @patch('djangocms_picture.backends.filer.get_thumbnailer')
    def test_get_image_url_with_size_options(self, mock_get_thumbnailer):
        """Test getting URL with size options."""
        mock_image = Mock(spec=['url'])
        mock_image.url = 'http://example.com/image.jpg'
        
        mock_thumbnailer = Mock()
        mock_thumbnail = Mock()
        mock_thumbnail.url = 'http://example.com/thumb.jpg'
        mock_thumbnailer.get_thumbnail.return_value = mock_thumbnail
        mock_get_thumbnailer.return_value = mock_thumbnailer
        
        size_options = {
            'size': (200, 150),
            'crop': True,
            'upscale': True,
            'quality': 85
        }
        
        result = self.backend.get_image_url(mock_image, size_options)
        
        self.assertEqual(result, 'http://example.com/thumb.jpg')
        mock_thumbnailer.get_thumbnail.assert_called_once_with({
            'size': (200, 150),
            'crop': True,
            'upscale': True,
            'quality': 85
        })

    @patch('djangocms_picture.backends.filer.get_thumbnailer')
    def test_get_image_url_with_subject_location(self, mock_get_thumbnailer):
        """Test getting URL with subject location."""
        mock_image = Mock()
        mock_image.url = 'http://example.com/image.jpg'
        mock_image.subject_location = '100,50'
        
        mock_thumbnailer = Mock()
        mock_thumbnail = Mock()
        mock_thumbnail.url = 'http://example.com/thumb.jpg'
        mock_thumbnailer.get_thumbnail.return_value = mock_thumbnail
        mock_get_thumbnailer.return_value = mock_thumbnailer
        
        size_options = {'size': (200, 150)}
        
        result = self.backend.get_image_url(mock_image, size_options)
        
        self.assertEqual(result, 'http://example.com/thumb.jpg')
        expected_options = {
            'size': (200, 150),
            'subject_location': '100,50'
        }
        mock_thumbnailer.get_thumbnail.assert_called_once_with(expected_options)

    @patch('djangocms_picture.backends.filer.get_thumbnailer')
    def test_get_image_url_thumbnail_exception(self, mock_get_thumbnailer):
        """Test fallback when thumbnail generation fails."""
        mock_image = Mock()
        mock_image.url = 'http://example.com/image.jpg'
        
        mock_thumbnailer = Mock()
        mock_thumbnailer.get_thumbnail.side_effect = Exception("Thumbnail error")
        mock_get_thumbnailer.return_value = mock_thumbnailer
        
        size_options = {'size': (200, 150)}
        
        result = self.backend.get_image_url(mock_image, size_options)
        
        # Should fallback to original image URL
        self.assertEqual(result, 'http://example.com/image.jpg')

    def test_get_srcset_data_no_image(self):
        """Test getting srcset data with no image."""
        result = self.backend.get_srcset_data(None, [768, 992])
        self.assertEqual(result, [])

    def test_get_srcset_data_no_breakpoints(self):
        """Test getting srcset data with no breakpoints."""
        mock_image = Mock()
        result = self.backend.get_srcset_data(mock_image, [])
        self.assertEqual(result, [])

    @patch('djangocms_picture.backends.filer.get_thumbnailer')
    def test_get_srcset_data_success(self, mock_get_thumbnailer):
        """Test successful srcset data generation."""
        mock_image = Mock()
        breakpoints = [768, 992, 1200]
        
        mock_thumbnailer = Mock()
        
        # Mock thumbnails for each breakpoint
        thumbnails = []
        for width in breakpoints:
            mock_thumbnail = Mock()
            mock_thumbnail.url = f'http://example.com/thumb_{width}.jpg'
            thumbnails.append(mock_thumbnail)
        
        mock_thumbnailer.get_thumbnail.side_effect = thumbnails
        mock_get_thumbnailer.return_value = mock_thumbnailer
        
        result = self.backend.get_srcset_data(mock_image, breakpoints, crop=True, quality=80)
        
        expected_result = [
            (768, 'http://example.com/thumb_768.jpg'),
            (992, 'http://example.com/thumb_992.jpg'),
            (1200, 'http://example.com/thumb_1200.jpg'),
        ]
        
        self.assertEqual(result, expected_result)
        self.assertEqual(mock_thumbnailer.get_thumbnail.call_count, 3)

    @patch('djangocms_picture.backends.filer.get_thumbnailer')
    def test_get_srcset_data_with_subject_location(self, mock_get_thumbnailer):
        """Test srcset data generation with subject location."""
        mock_image = Mock()
        mock_image.subject_location = '100,50'
        breakpoints = [768]
        
        mock_thumbnailer = Mock()
        mock_thumbnail = Mock()
        mock_thumbnail.url = 'http://example.com/thumb.jpg'
        mock_thumbnailer.get_thumbnail.return_value = mock_thumbnail
        mock_get_thumbnailer.return_value = mock_thumbnailer
        
        result = self.backend.get_srcset_data(mock_image, breakpoints)
        
        expected_options = {
            'size': (768, 768),
            'crop': False,
            'quality': 90,
            'subject_location': '100,50'
        }
        mock_thumbnailer.get_thumbnail.assert_called_once_with(expected_options)

    @patch('djangocms_picture.backends.filer.get_thumbnailer')
    def test_get_srcset_data_thumbnail_exception(self, mock_get_thumbnailer):
        """Test srcset data generation with thumbnail failures."""
        mock_image = Mock()
        breakpoints = [768, 992]
        
        mock_thumbnailer = Mock()
        # First call succeeds, second fails
        mock_thumbnail = Mock()
        mock_thumbnail.url = 'http://example.com/thumb_768.jpg'
        mock_thumbnailer.get_thumbnail.side_effect = [mock_thumbnail, Exception("Error")]
        mock_get_thumbnailer.return_value = mock_thumbnailer
        
        result = self.backend.get_srcset_data(mock_image, breakpoints)
        
        # Should only include successful thumbnail
        expected_result = [(768, 'http://example.com/thumb_768.jpg')]
        self.assertEqual(result, expected_result)

    @patch('djangocms_picture.backends.filer.get_thumbnailer')
    def test_delete_image_success(self, mock_get_thumbnailer):
        """Test successful image deletion."""
        mock_image = Mock()
        
        mock_thumbnailer = Mock()
        mock_get_thumbnailer.return_value = mock_thumbnailer
        
        self.backend.delete_image(mock_image)
        
        mock_thumbnailer.delete_thumbnails.assert_called_once()
        mock_image.delete.assert_called_once()

    @patch('djangocms_picture.backends.filer.get_thumbnailer')
    def test_delete_image_thumbnail_deletion_error(self, mock_get_thumbnailer):
        """Test image deletion when thumbnail deletion fails."""
        mock_image = Mock()
        
        mock_thumbnailer = Mock()
        mock_thumbnailer.delete_thumbnails.side_effect = Exception("Delete error")
        mock_get_thumbnailer.return_value = mock_thumbnailer
        
        self.backend.delete_image(mock_image)
        
        # Should still delete the main image even if thumbnail deletion fails
        mock_image.delete.assert_called_once()

    def test_delete_image_none(self):
        """Test deleting None image reference."""
        # Should not raise any error
        self.backend.delete_image(None)

    def test_get_image_info_no_image(self):
        """Test getting image info with no image."""
        result = self.backend.get_image_info(None)
        self.assertEqual(result, {})

    def test_get_image_info_success(self):
        """Test getting image info successfully."""
        mock_image = Mock()
        mock_image.width = 800
        mock_image.height = 600
        mock_image.file_type = 'jpeg'
        mock_image.size = 102400
        mock_image.default_alt_text = 'Test alt text'
        mock_image.default_caption = 'Test caption'
        mock_image.original_filename = 'test.jpg'
        mock_image.label = 'Test label'
        
        result = self.backend.get_image_info(mock_image)
        
        expected_info = {
            'width': 800,
            'height': 600,
            'format': 'JPEG',
            'size': 102400,
            'alt_text': 'Test alt text',
            'caption': 'Test caption',
            'filename': 'test.jpg',
            'label': 'Test label',
        }
        
        self.assertEqual(result, expected_info)

    def test_get_image_info_missing_attributes(self):
        """Test getting image info when attributes are missing."""
        mock_image = Mock(spec=[])  # Mock with no attributes
        
        result = self.backend.get_image_info(mock_image)
        
        expected_info = {
            'width': None,
            'height': None,
            'format': '',
            'size': 0,
            'alt_text': '',
            'caption': '',
            'filename': '',
            'label': '',
        }
        
        self.assertEqual(result, expected_info)

    def test_validate_image_allowed_content_type(self):
        """Test validation with allowed content type."""
        mock_file = Mock(spec=['content_type'])
        mock_file.content_type = 'image/jpeg'
        
        # Should not raise any exception
        self.backend.validate_image(mock_file)

    def test_validate_image_disallowed_content_type(self):
        """Test validation with disallowed content type."""
        mock_file = Mock(spec=['content_type'])
        mock_file.content_type = 'image/bmp'
        
        with self.assertRaises(ValidationError) as cm:
            self.backend.validate_image(mock_file)
        
        self.assertIn('File type not allowed', str(cm.exception))

    def test_validate_image_custom_allowed_types(self):
        """Test validation with custom allowed types."""
        mock_file = Mock(spec=['content_type'])
        mock_file.content_type = 'image/png'
        
        # Should not raise with png in allowed types
        self.backend.validate_image(mock_file, allowed_types=['png', 'gif'])
        
        # Should raise with jpg not in allowed types
        mock_file.content_type = 'image/jpeg'
        with self.assertRaises(ValidationError):
            self.backend.validate_image(mock_file, allowed_types=['png', 'gif'])

    def test_validate_image_file_size_valid(self):
        """Test validation with valid file size."""
        mock_file = Mock(spec=['content_type', 'size'])
        mock_file.content_type = 'image/jpeg'
        mock_file.size = 500000  # 500KB
        
        # Should not raise with 1MB limit
        self.backend.validate_image(mock_file, max_size=1024*1024)

    def test_validate_image_file_size_too_large(self):
        """Test validation with too large file size."""
        mock_file = Mock(spec=['content_type', 'size'])
        mock_file.content_type = 'image/jpeg'
        mock_file.size = 2 * 1024 * 1024  # 2MB
        
        with self.assertRaises(ValidationError) as cm:
            self.backend.validate_image(mock_file, max_size=1024*1024)  # 1MB limit
        
        self.assertIn('File too large', str(cm.exception))

    def test_validate_image_dimensions_valid(self):
        """Test validation with valid dimensions."""
        mock_file = Mock(spec=['content_type', 'width', 'height'])
        mock_file.content_type = 'image/jpeg'
        mock_file.width = 800
        mock_file.height = 600
        
        # Should not raise
        self.backend.validate_image(
            mock_file,
            min_width=100,
            min_height=100,
            max_width=1000,
            max_height=1000
        )

    def test_validate_image_width_too_small(self):
        """Test validation with width too small."""
        mock_file = Mock(spec=['content_type', 'width', 'height'])
        mock_file.content_type = 'image/jpeg'
        mock_file.width = 50
        mock_file.height = 600
        
        with self.assertRaises(ValidationError) as cm:
            self.backend.validate_image(mock_file, min_width=100)
        
        self.assertIn('Image width too small', str(cm.exception))

    def test_validate_image_height_too_small(self):
        """Test validation with height too small."""
        mock_file = Mock(spec=['content_type', 'width', 'height'])
        mock_file.content_type = 'image/jpeg'
        mock_file.width = 800
        mock_file.height = 50
        
        with self.assertRaises(ValidationError) as cm:
            self.backend.validate_image(mock_file, min_height=100)
        
        self.assertIn('Image height too small', str(cm.exception))

    def test_validate_image_width_too_large(self):
        """Test validation with width too large."""
        mock_file = Mock(spec=['content_type', 'width', 'height'])
        mock_file.content_type = 'image/jpeg'
        mock_file.width = 2000
        mock_file.height = 600
        
        with self.assertRaises(ValidationError) as cm:
            self.backend.validate_image(mock_file, max_width=1000)
        
        self.assertIn('Image width too large', str(cm.exception))

    def test_validate_image_height_too_large(self):
        """Test validation with height too large."""
        mock_file = Mock(spec=['content_type', 'width', 'height'])
        mock_file.content_type = 'image/jpeg'
        mock_file.width = 800
        mock_file.height = 2000
        
        with self.assertRaises(ValidationError) as cm:
            self.backend.validate_image(mock_file, max_height=1000)
        
        self.assertIn('Image height too large', str(cm.exception))

    def test_get_field_class(self):
        """Test getting field class."""
        from filer.fields.image import FilerImageField
        
        result = self.backend.get_field_class()
        self.assertEqual(result, FilerImageField)

    def test_get_field_kwargs_defaults(self):
        """Test getting field kwargs with defaults."""
        result = self.backend.get_field_kwargs()
        
        # Test that the basic structure is correct
        self.assertEqual(result['blank'], True)
        self.assertEqual(result['null'], True)
        self.assertEqual(result['related_name'], '+')
        # on_delete will be a function object in Django, not a string
        from django.db import models
        self.assertEqual(result['on_delete'], models.SET_NULL)

    def test_get_field_kwargs_custom_options(self):
        """Test getting field kwargs with custom options."""
        result = self.backend.get_field_kwargs(
            blank=False,
            null=False,
            on_delete='CASCADE',
            related_name='pictures'
        )
        
        self.assertEqual(result['blank'], False)
        self.assertEqual(result['null'], False)
        self.assertEqual(result['related_name'], 'pictures')
        # on_delete will be converted to the actual models constant
        from django.db import models
        self.assertEqual(result['on_delete'], models.CASCADE)

    def test_get_field_kwargs_on_delete_conversion(self):
        """Test conversion of on_delete string to models constant."""
        result = self.backend.get_field_kwargs(on_delete='CASCADE')
        
        # Should convert string to models constant
        from django.db import models
        self.assertEqual(result['on_delete'], models.CASCADE) 