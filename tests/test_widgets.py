"""
Tests for djangocms-picture widgets.
"""
import json
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.widgets import Media
from django.test import TestCase

from djangocms_picture.fields import PictureData
from djangocms_picture.widgets import PictureWidget, SimpleImageWidget


class PictureWidgetTestCase(TestCase):
    """Test PictureWidget functionality."""

    def setUp(self):
        """Set up test environment."""
        self.widget = PictureWidget()
        self.test_image_file = SimpleUploadedFile(
            "test.jpg",
            b"fake image data",
            content_type="image/jpeg"
        )

    def test_init_defaults(self):
        """Test widget initialization with defaults."""
        widget = PictureWidget()
        
        self.assertIsNone(widget.backend_name)
        self.assertTrue(widget.responsive)
        self.assertEqual(widget.breakpoints, [576, 768, 992, 1200])
        self.assertEqual(widget.formats, ['webp', 'jpeg', 'png'])
        self.assertTrue(widget.allow_links)
        self.assertEqual(len(widget.alignment_choices), 3)
        self.assertIsNone(widget.max_size)

    def test_init_custom_options(self):
        """Test widget initialization with custom options."""
        widget = PictureWidget(
            backend='filer',
            responsive=False,
            breakpoints=[768, 992],
            formats=['jpeg', 'png'],
            allow_links=False,
            alignment_choices=[('left', 'Left')],
            max_size=1024*1024
        )
        
        self.assertEqual(widget.backend_name, 'filer')
        self.assertFalse(widget.responsive)
        self.assertEqual(widget.breakpoints, [768, 992])
        self.assertEqual(widget.formats, ['jpeg', 'png'])
        self.assertFalse(widget.allow_links)
        self.assertEqual(widget.alignment_choices, [('left', 'Left')])
        self.assertEqual(widget.max_size, 1024*1024)

    def test_get_backend(self):
        """Test getting backend."""
        widget = PictureWidget(backend='filer')
        
        with patch('djangocms_picture.widgets.backend_registry.get_backend') as mock_get:
            mock_backend = Mock()
            mock_get.return_value = mock_backend
            
            result = widget.get_backend()
            
            self.assertEqual(result, mock_backend)
            mock_get.assert_called_once_with('filer')

    def test_format_value_empty(self):
        """Test formatting empty value."""
        result = self.widget.format_value(None)
        self.assertEqual(result, '')
        
        result = self.widget.format_value('')
        self.assertEqual(result, '')

    def test_format_value_picture_data(self):
        """Test formatting PictureData object."""
        picture_data = Mock()
        picture_data.to_json.return_value = '{"width": 800}'
        
        result = self.widget.format_value(picture_data)
        
        self.assertEqual(result, '{"width": 800}')
        picture_data.to_json.assert_called_once()

    def test_format_value_dict(self):
        """Test formatting dict value."""
        test_dict = {'width': 800, 'height': 600}
        
        result = self.widget.format_value(test_dict)
        
        parsed = json.loads(result)
        self.assertEqual(parsed['width'], 800)
        self.assertEqual(parsed['height'], 600)

    def test_format_value_string(self):
        """Test formatting string value."""
        result = self.widget.format_value('test_value')
        self.assertEqual(result, 'test_value')

    def test_value_from_datadict_no_data(self):
        """Test extracting value with no data."""
        data = {}
        files = {}
        
        result = self.widget.value_from_datadict(data, files, 'picture')
        
        self.assertEqual(result, '{}')

    def test_value_from_datadict_with_data(self):
        """Test extracting value with JSON data."""
        data = {'picture': '{"width": 800}'}
        files = {}
        
        result = self.widget.value_from_datadict(data, files, 'picture')
        
        self.assertEqual(result, '{"width": 800}')

    def test_value_from_datadict_with_file_upload(self):
        """Test extracting value with file upload."""
        data = {'picture': '{"width": 800}'}
        files = {'picture_file': self.test_image_file}
        
        result = self.widget.value_from_datadict(data, files, 'picture')
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['width'], 800)
        self.assertEqual(result['uploaded_file'], self.test_image_file)

    def test_value_from_datadict_with_file_upload_invalid_json(self):
        """Test extracting value with file upload and invalid JSON."""
        data = {'picture': 'invalid json'}
        files = {'picture_file': self.test_image_file}
        
        result = self.widget.value_from_datadict(data, files, 'picture')
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['uploaded_file'], self.test_image_file)

    def test_value_from_datadict_with_file_upload_no_existing_data(self):
        """Test extracting value with file upload and no existing data."""
        data = {}
        files = {'picture_file': self.test_image_file}
        
        result = self.widget.value_from_datadict(data, files, 'picture')
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['uploaded_file'], self.test_image_file)

    @patch('djangocms_picture.widgets.render_to_string')
    def test_render_with_template(self, mock_render):
        """Test rendering with template."""
        mock_render.return_value = '<div>Widget HTML</div>'
        picture_data = PictureData({'width': 800})
        
        with patch.object(self.widget, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_get_backend.return_value = mock_backend
            
            result = self.widget.render('picture', picture_data, {'class': 'test'})
            
            self.assertEqual(result, '<div>Widget HTML</div>')
            mock_render.assert_called_once()
            
            # Check context passed to template
            context = mock_render.call_args[0][1]
            self.assertEqual(context['name'], 'picture')
            self.assertEqual(context['value'], picture_data)
            self.assertEqual(context['attrs'], {'class': 'test'})
            self.assertEqual(context['backend'], mock_backend)

    @patch('djangocms_picture.widgets.render_to_string')
    def test_render_with_string_value(self, mock_render):
        """Test rendering with string value."""
        mock_render.return_value = '<div>Widget HTML</div>'
        
        with patch.object(self.widget, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_get_backend.return_value = mock_backend
            
            result = self.widget.render('picture', '{"width": 800}')
            
            self.assertEqual(result, '<div>Widget HTML</div>')
            
            # Check that value was converted to PictureData
            context = mock_render.call_args[0][1]
            self.assertIsInstance(context['value'], PictureData)

    @patch('djangocms_picture.widgets.render_to_string')
    def test_render_with_invalid_json(self, mock_render):
        """Test rendering with invalid JSON value."""
        mock_render.return_value = '<div>Widget HTML</div>'
        
        with patch.object(self.widget, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_get_backend.return_value = mock_backend
            
            result = self.widget.render('picture', 'invalid json')
            
            # Should create empty PictureData
            context = mock_render.call_args[0][1]
            self.assertIsInstance(context['value'], PictureData)

    @patch('djangocms_picture.widgets.render_to_string')
    def test_render_template_exception_fallback(self, mock_render):
        """Test rendering fallback when template fails."""
        mock_render.side_effect = Exception("Template error")
        picture_data = PictureData({'width': 800})
        
        with patch.object(self.widget, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_get_backend.return_value = mock_backend
            
            result = self.widget.render('picture', picture_data)
            
            # Should use fallback rendering
            self.assertIn('djangocms-picture-widget', result)
            self.assertIn('picture', result)

    def test_render_fallback(self):
        """Test fallback rendering method."""
        picture_data = PictureData({'width': 800, 'height': 600})
        attrs = {'class': 'test'}
        
        result = self.widget._render_fallback('picture', picture_data, attrs)
        
        self.assertIn('djangocms-picture-widget', result)
        self.assertIn('data-name="picture"', result)
        self.assertIn('type="hidden"', result)
        self.assertIn('picture_file', result)

    def test_render_fallback_long_value(self):
        """Test fallback rendering with long JSON value."""
        # Create a long JSON string by setting multiple properties
        picture_data = PictureData()
        picture_data.alt_text = 'x' * 50
        picture_data.caption = 'y' * 50
        picture_data.image_reference = 'z' * 50
        picture_data.external_url = 'http://example.com/' + 'a' * 50 + '.jpg'
        attrs = {}
        
        result = self.widget._render_fallback('picture', picture_data, attrs)
        
        # Should truncate long values
        self.assertIn('...', result)

    def test_media_property(self):
        """Test widget media property."""
        media = self.widget.media
        
        self.assertIsInstance(media, Media)
        self.assertIn('djangocms_picture/css/picture-widget.css', str(media))
        self.assertIn('djangocms_picture/js/picture-widget.js', str(media))

    def test_value_omitted_from_data_present(self):
        """Test value_omitted_from_data when data is present."""
        data = {'picture': '{"width": 800}'}
        files = {}
        
        result = self.widget.value_omitted_from_data(data, files, 'picture')
        
        self.assertFalse(result)

    def test_value_omitted_from_data_file_present(self):
        """Test value_omitted_from_data when file is present."""
        data = {}
        files = {'picture_file': self.test_image_file}
        
        result = self.widget.value_omitted_from_data(data, files, 'picture')
        
        self.assertFalse(result)

    def test_value_omitted_from_data_both_present(self):
        """Test value_omitted_from_data when both data and file are present."""
        data = {'picture': '{"width": 800}'}
        files = {'picture_file': self.test_image_file}
        
        result = self.widget.value_omitted_from_data(data, files, 'picture')
        
        self.assertFalse(result)

    def test_value_omitted_from_data_neither_present(self):
        """Test value_omitted_from_data when neither data nor file are present."""
        data = {}
        files = {}
        
        result = self.widget.value_omitted_from_data(data, files, 'picture')
        
        self.assertTrue(result)

    def test_render_context_max_size_mb(self):
        """Test that max_size_mb is calculated correctly in render context."""
        widget = PictureWidget(max_size=2 * 1024 * 1024)  # 2MB
        
        with patch('djangocms_picture.widgets.render_to_string') as mock_render:
            mock_render.return_value = '<div>Widget HTML</div>'
            with patch.object(widget, 'get_backend') as mock_get_backend:
                mock_backend = Mock()
                mock_get_backend.return_value = mock_backend
                
                widget.render('picture', PictureData())
                
                context = mock_render.call_args[0][1]
                self.assertEqual(context['max_size_mb'], 2.0)

    def test_render_context_no_max_size(self):
        """Test render context when max_size is None."""
        widget = PictureWidget(max_size=None)
        
        with patch('djangocms_picture.widgets.render_to_string') as mock_render:
            mock_render.return_value = '<div>Widget HTML</div>'
            with patch.object(widget, 'get_backend') as mock_get_backend:
                mock_backend = Mock()
                mock_get_backend.return_value = mock_backend
                
                widget.render('picture', PictureData())
                
                context = mock_render.call_args[0][1]
                self.assertIsNone(context['max_size_mb'])


class SimpleImageWidgetTestCase(TestCase):
    """Test SimpleImageWidget functionality."""

    def setUp(self):
        """Set up test environment."""
        self.widget = SimpleImageWidget()

    def test_init_defaults(self):
        """Test widget initialization with defaults."""
        widget = SimpleImageWidget()
        
        self.assertIsNone(widget.backend_name)

    def test_init_custom_backend(self):
        """Test widget initialization with custom backend."""
        widget = SimpleImageWidget(backend='filer')
        
        self.assertEqual(widget.backend_name, 'filer')

    def test_get_backend(self):
        """Test getting backend."""
        widget = SimpleImageWidget(backend='filer')
        
        with patch('djangocms_picture.widgets.backend_registry.get_backend') as mock_get:
            mock_backend = Mock()
            mock_get.return_value = mock_backend
            
            result = widget.get_backend()
            
            self.assertEqual(result, mock_backend)
            mock_get.assert_called_once_with('filer')

    @patch('djangocms_picture.widgets.render_to_string')
    def test_render_with_template(self, mock_render):
        """Test rendering with template."""
        mock_render.return_value = '<input type="file" />'
        
        with patch.object(self.widget, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_get_backend.return_value = mock_backend
            
            result = self.widget.render('image', 'test_value', {'class': 'test'})
            
            self.assertEqual(result, '<input type="file" />')
            mock_render.assert_called_once()
            
            # Check context passed to template
            context = mock_render.call_args[0][1]
            self.assertEqual(context['name'], 'image')
            self.assertEqual(context['value'], 'test_value')
            self.assertEqual(context['attrs'], {'class': 'test'})
            self.assertEqual(context['backend'], mock_backend)

    @patch('djangocms_picture.widgets.render_to_string')
    def test_render_template_exception_fallback(self, mock_render):
        """Test rendering fallback when template fails."""
        mock_render.side_effect = Exception("Template error")
        
        with patch.object(self.widget, 'get_backend') as mock_get_backend:
            mock_backend = Mock()
            mock_get_backend.return_value = mock_backend
            
            result = self.widget.render('image', 'test_value')
            
            # Should use fallback rendering (file input)
            self.assertIn('type="file"', result)
            self.assertIn('name="image"', result)
            self.assertIn('accept="image/*"', result)

    def test_render_no_attrs(self):
        """Test rendering with no attributes."""
        with patch('djangocms_picture.widgets.render_to_string') as mock_render:
            mock_render.return_value = '<input type="file" />'
            with patch.object(self.widget, 'get_backend') as mock_get_backend:
                mock_backend = Mock()
                mock_get_backend.return_value = mock_backend
                
                result = self.widget.render('image', 'test_value')
                
                context = mock_render.call_args[0][1]
                self.assertEqual(context['attrs'], {})

    def test_media_property(self):
        """Test widget media property."""
        media = self.widget.media
        
        self.assertIsInstance(media, Media)
        self.assertIn('djangocms_picture/css/simple-image-widget.css', str(media))
        self.assertIn('djangocms_picture/js/simple-image-widget.js', str(media))


class WidgetExportsTestCase(TestCase):
    """Test widget module exports."""

    def test_all_exports(self):
        """Test that __all__ contains expected widgets."""
        from djangocms_picture.widgets import __all__
        
        expected = ['PictureWidget', 'SimpleImageWidget']
        self.assertEqual(__all__, expected) 