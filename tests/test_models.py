from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase

from cms.api import create_page

from easy_thumbnails.files import ThumbnailFile
from filer.models import ThumbnailOption

from djangocms_picture.models import (
    LINK_TARGET, PICTURE_RATIO, RESPONSIVE_IMAGE_CHOICES, Picture,
    get_alignment, get_templates,
)

from .helpers import get_filer_image


class PictureModelTestCase(TestCase):

    def setUp(self):
        self.page = create_page(
            title="help",
            template="page.html",
            language="en",
        )
        self.picture = Picture.objects.create(
            template="default",
            picture=get_filer_image(),
            width=720,
            height=480,
            alignment=get_alignment()[0][0],
            caption_text="some caption",
            attributes="{'data-type', 'picture'}",
            link_url="http://www.divio.com",
            link_page=self.page,
            link_target=LINK_TARGET[0][0],
            link_attributes="{'data-type', 'picture'}",
        )
        self.external_picture = 'https://www.google.com/images/logo.png'

    def tearDown(self):
        self.page.delete()

    def test_settings(self):
        self.assertEqual(get_templates(), [('default', 'Default')])
        settings.DJANGOCMS_PICTURE_TEMPLATES = [('feature', 'Feature')]
        self.assertEqual(get_templates(), [('default', 'Default'), ('feature', 'Feature')])

        self.assertEqual(PICTURE_RATIO, 1.6180)
        self.assertEqual(
            get_alignment(),
            (('left', 'Align left'), ('right', 'Align right'), ('center', 'Align center')),
        )

    def test_picture_instance(self):
        instance = Picture.objects.all()
        self.assertEqual(instance.count(), 1)
        instance = Picture.objects.first()
        self.assertEqual(instance.template, "default")
        self.assertEqual(instance.picture.label, "test_file.jpg")
        self.assertEqual(instance.width, 720)
        self.assertEqual(instance.height, 480)
        self.assertEqual(instance.alignment, "left")
        self.assertEqual(instance.caption_text, "some caption")
        self.assertEqual(instance.attributes, "{'data-type', 'picture'}")
        self.assertEqual(instance.link_url, "http://www.divio.com")
        self.assertEqual(instance.link_page, self.page)
        self.assertEqual(instance.link_target, "_blank")
        self.assertEqual(instance.link_attributes, "{'data-type', 'picture'}")
        # test strings
        self.assertEqual(str(instance), "test_file.jpg")
        self.assertEqual(instance.get_short_description(), "test_file.jpg")
        instance.external_picture = self.external_picture
        self.assertEqual(instance.get_short_description(), self.external_picture)
        instance.picture = None
        instance.external_picture = None
        self.assertEqual(str(instance), "1")
        self.assertEqual(instance.get_short_description(), "<file is missing>")
        self.assertIsNone(instance.copy_relations(instance))

    def test_clean(self):
        # test when internal and external links are given
        instance = self.picture
        with self.assertRaises(ValidationError):
            instance.clean()  # either external or internal link is allowed
        instance.link_url = None
        instance.clean()
        # test when image is missing
        instance.picture = None
        instance.external_picture = None
        with self.assertRaises(ValidationError):
            instance.clean()  # You need to add an image
        instance.external_picture = self.external_picture
        instance.clean()
        # test invalid option pairs
        instance.use_automatic_scaling = True
        instance.use_no_cropping = True
        with self.assertRaises(ValidationError):
            instance.clean()  # invalid option pair given
        instance.use_no_cropping = False
        instance.clean()

    def test_get_size(self):
        instance = self.picture
        self.assertEqual(
            instance.get_size(),
            {"size": (800, 600), "crop": False, "upscale": False},
        )
        instance.use_crop = True
        self.assertEqual(
            instance.get_size(),
            {"size": (800, 600), "crop": True, "upscale": False},
        )
        instance.use_upscale = True
        self.assertEqual(
            instance.get_size(),
            {"size": (800, 600), "crop": True, "upscale": True},
        )
        # test different size outputs
        self.assertEqual(
            instance.get_size(width=1000),
            {'size': (1000, 618), 'crop': True, 'upscale': True},
        )
        self.assertEqual(
            instance.get_size(height=1000),
            {'size': (1618, 1000), 'crop': True, 'upscale': True},
        )
        self.assertEqual(
            instance.get_size(width=1000, height=1000),
            {'size': (1000, 1000), 'crop': True, 'upscale': True},
        )
        instance.use_automatic_scaling = False
        self.assertEqual(
            instance.get_size(),
            {'size': (720, 480), 'crop': True, 'upscale': True},
        )
        # setup thumbnail options
        instance.thumbnail_options = ThumbnailOption.objects.create(
            name="example",
            width=200,
            height=200,
            crop=False,
            upscale=False,
        )
        self.assertEqual(
            instance.get_size(),
            {'size': (200, 200), 'crop': False, 'upscale': False},
        )

    def test_get_link(self):
        instance = self.picture
        instance.external_picture = self.external_picture
        self.assertEqual(instance.get_link(), "http://www.divio.com")
        instance.link_url = None
        self.assertEqual(instance.get_link(), self.page.get_absolute_url())
        instance.link_page = None
        self.assertEqual(instance.get_link(), self.external_picture)
        instance.external_picture = None
        self.assertFalse(instance.get_link())

    def test_is_responsive_image(self):
        instance = self.picture
        self.assertTrue(instance.is_responsive_image)
        instance.use_responsive_image = RESPONSIVE_IMAGE_CHOICES[2][0]
        self.assertFalse(instance.is_responsive_image)
        instance.external_picture = self.external_picture
        self.assertFalse(instance.is_responsive_image)

    def test_img_srcset_data(self):
        instance = self.picture
        self.assertIsInstance(
            instance.img_srcset_data[0][1],
            ThumbnailFile,
        )
        instance.external_picture = self.external_picture
        self.assertIsNone(instance.img_srcset_data)

    def test_img_src(self):
        instance = self.picture
        # thumbnail is generated
        self.assertIn(
            "/media/filer_public_thumbnails/filer_public/",
            instance.img_src,
        )
        # no thumbnail is generated
        instance.use_no_cropping = True
        self.assertIn(
            "/media/filer_public/",
            instance.img_src,
        )
        instance.picture = None
        self.assertEqual(instance.img_src, "")
        instance.external_picture = self.external_picture
        self.assertEqual(instance.img_src, self.external_picture)
