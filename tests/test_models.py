# -*- coding: utf-8 -*-
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File as DjangoFile

from cms.api import add_plugin, create_page

from djangocms_helper.base_test import BaseTestCase
from easy_thumbnails.files import ThumbnailFile
from filer.models.imagemodels import Image as FilerImage
from filer.utils.compatibility import PILImage, PILImageDraw

from djangocms_picture.models import Picture


# from https://github.com/divio/django-filer/blob/develop/tests/helpers.py#L46-L52
def create_image(mode="RGB", size=(800, 600)):
    image = PILImage.new(mode, size)
    draw = PILImageDraw.Draw(image)
    x_bit, y_bit = size[0] // 10, size[1] // 10
    draw.rectangle((x_bit, y_bit * 2, x_bit * 7, y_bit * 3), "red")
    draw.rectangle((x_bit * 2, y_bit, x_bit * 3, y_bit * 8), "red")
    return image


class PictureTestCase(BaseTestCase):

    def setUp(self):
        self.external_picture = 'https://www.google.com/images/logo.png'
        self.page = create_page(
            title='help',
            template='page.html',
            language='en',
        )
        self.img = create_image()
        self.image_name = "test_file.jpg"
        self.filename = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, self.image_name)
        self.img.save(self.filename, "JPEG")
        self.filer_object = None

    def tearDown(self):
        os.remove(self.filename)
        self.page.delete()
        if self.filer_object:
            self.filer_object.delete()

    def create_filer_file(self):
        filer_file = DjangoFile(open(self.filename, "rb"), name=self.image_name)
        self.filer_object = FilerImage.objects.create(
            original_filename=self.image_name,
            file=filer_file,
        )
        return self.filer_object

    def test_picture_instance(self):
        """Picture instance has been created"""
        Picture.objects.create(
            external_picture=self.external_picture,
        )
        picture = Picture.objects.get(external_picture=self.external_picture)
        self.assertEqual(picture.external_picture, self.external_picture)

    def test_blank_picture(self):
        plugin = add_plugin(
            self.page.placeholders.get(slot="content"),
            "PicturePlugin",
            "en",
        )
        self.assertEqual(plugin.picture, None)
        self.assertEqual(plugin.get_short_description(), "<file is missing>")
        self.assertEqual(plugin.get_size(), {
            'size': (None, None),
            'crop': False,
            'upscale': False,
        })
        self.assertEqual(plugin.get_link(), False)
        # shall return validation error as there is no picture defined
        with self.assertRaises(ValidationError):
            plugin.clean()
        self.assertEqual(plugin.is_responsive_image, True)
        self.assertEqual(plugin.img_srcset_data, None)
        self.assertEqual(plugin.img_src, '')

    def test_picture(self):
        sample_file = self.create_filer_file()

        plugin = add_plugin(
            self.page.placeholders.get(slot="content"),
            "PicturePlugin",
            "en",
            picture=sample_file,
            link_page_id=self.page.pk,
        )
        self.assertEqual(plugin.picture, sample_file)
        self.assertEqual(plugin.get_short_description(), "test_file.jpg")
        self.assertEqual(plugin.get_size(), {
            'size': (800, 600),
            'crop': False,
            'upscale': False,
        })
        self.assertEqual(plugin.get_link(), "/en/help/")
        self.assertEqual(plugin.clean(), None)
        self.assertEqual(plugin.is_responsive_image, True)
        self.assertIsInstance(plugin.img_srcset_data[0][1], ThumbnailFile)
        self.assertIn('test_file.jpg__800x600_q85_subsampling', plugin.img_src)

    def test_external_picture(self):
        plugin = add_plugin(
            self.page.placeholders.get(slot="content"),
            "PicturePlugin",
            "en",
            external_picture=self.external_picture,
        )
        self.assertEqual(plugin.get_link(), self.external_picture)
        self.assertEqual(plugin.img_src, self.external_picture)
        self.assertEqual(plugin.is_responsive_image, False)
        self.assertEqual(plugin.img_srcset_data, None)

        # tests when internal and external pictures are supplied
        # external picture shall thake priority
        sample_file = self.create_filer_file()
        plugin = add_plugin(
            self.page.placeholders.get(slot="content"),
            "PicturePlugin",
            "en",
            picture=sample_file,
            external_picture=self.external_picture,
        )
        self.assertEqual(plugin.get_link(), self.external_picture)
        self.assertEqual(plugin.img_src, self.external_picture)
        self.assertEqual(plugin.is_responsive_image, False)
        self.assertEqual(plugin.img_srcset_data, None)
