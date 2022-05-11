from django.core.exceptions import ValidationError
from django.test import TestCase

from cms.api import create_page

from filer.models import ThumbnailOption

from djangocms_picture.models import (
    ALTERNATIVE_FORMAT_WEBP_CHOICES, LINK_TARGET, USE_RESPONSIVE_IMAGE_CHOICES,
    Picture, get_alignment, get_templates,
)
from djangocms_picture.settings import (
    PICTURE_RATIO, RESPONSIVE_IMAGE_SIZES,
    RESPONSIVE_IMAGES_ALTERNATIVE_FORMAT_WEBP,
    RESPONSIVE_IMAGES_BREAKPOINT_LARGE_ID,
    RESPONSIVE_IMAGES_BREAKPOINT_MEDIUM_ID,
    RESPONSIVE_IMAGES_BREAKPOINT_SMALL_ID, RESPONSIVE_IMAGES_BREAKPOINTS,
    RESPONSIVE_IMAGES_ENABLED,
)
from djangocms_picture.types import AlternativePictureData, SizesAttributeData

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

        # Ensure picture.picture is the one loaded from DB and not the one given for object creation
        self.picture.refresh_from_db()

        self.external_picture = 'https://www.google.com/images/logo.png'

    def tearDown(self):
        self.page.delete()

    def test_settings(self):
        self.assertEqual(get_templates(), [('default', 'Default'), ('feature', 'Feature')])

        self.assertEqual(PICTURE_RATIO, 1.6180)
        self.assertEqual(
            get_alignment(),
            (('left', 'Align left'), ('right', 'Align right'), ('center', 'Align center')),
        )
        self.assertTrue(RESPONSIVE_IMAGES_ENABLED)
        self.assertEqual([542, 768, 992], RESPONSIVE_IMAGE_SIZES)
        self.assertEqual(642, RESPONSIVE_IMAGES_BREAKPOINTS[RESPONSIVE_IMAGES_BREAKPOINT_MEDIUM_ID])
        self.assertEqual(1042, RESPONSIVE_IMAGES_BREAKPOINTS[RESPONSIVE_IMAGES_BREAKPOINT_LARGE_ID])
        self.assertTrue(RESPONSIVE_IMAGES_ALTERNATIVE_FORMAT_WEBP)

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
        self.assertIsInstance(instance.get_size()["size"][0], int)
        self.assertIsInstance(instance.get_size()["size"][1], int)

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
        instance.use_responsive_image = USE_RESPONSIVE_IMAGE_CHOICES[2][0]
        self.assertFalse(instance.is_responsive_image)
        instance.external_picture = self.external_picture
        self.assertFalse(instance.is_responsive_image)

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

    def test_get_picture(self):
        instance = self.picture
        instance.medium_screen_picture = get_filer_image()
        instance.large_screen_picture = get_filer_image()

        self.assertEqual(instance.picture, instance.get_picture(RESPONSIVE_IMAGES_BREAKPOINT_SMALL_ID))
        self.assertEqual(instance.medium_screen_picture, instance.get_picture(RESPONSIVE_IMAGES_BREAKPOINT_MEDIUM_ID))
        self.assertEqual(instance.large_screen_picture, instance.get_picture(RESPONSIVE_IMAGES_BREAKPOINT_LARGE_ID))

    def test_get_picture_viewport_width(self):
        instance = self.picture
        instance.small_screen_viewport_width = 12
        instance.medium_screen_viewport_width = 13
        instance.large_screen_viewport_width = 14

        self.assertEqual(12, instance.get_picture_viewport_width(RESPONSIVE_IMAGES_BREAKPOINT_SMALL_ID))
        self.assertEqual(13, instance.get_picture_viewport_width(RESPONSIVE_IMAGES_BREAKPOINT_MEDIUM_ID))
        self.assertEqual(14, instance.get_picture_viewport_width(RESPONSIVE_IMAGES_BREAKPOINT_LARGE_ID))

    def test_generate_alternative_format_webp(self):
        instance = self.picture
        self.assertTrue(instance.generate_alternative_format_webp)
        instance.alternative_format_webp = ALTERNATIVE_FORMAT_WEBP_CHOICES[2][0]
        self.assertFalse(instance.generate_alternative_format_webp)

    def test_get_alternative_picture_data(self):
        instance = self.picture
        # instance.medium_screen_picture = get_filer_image()
        # instance.large_screen_picture = get_filer_image()
        instance.small_screen_viewport_width = 12
        instance.medium_screen_viewport_width = 13
        instance.large_screen_viewport_width = 14

        self.assertEqual(
            AlternativePictureData(
                size_id=RESPONSIVE_IMAGES_BREAKPOINT_SMALL_ID,
                picture=instance.picture,
                viewport_width=12,
                sizes_data=[
                    SizesAttributeData(1042, 14, []),
                    SizesAttributeData(642, 13, []),
                    SizesAttributeData(0, 12, []),
                ],
            ),
            instance.get_alternative_picture_data(RESPONSIVE_IMAGES_BREAKPOINT_SMALL_ID)
        )

    def test_alternative_pictures_data(self):
        instance = self.picture
        # instance.medium_screen_picture = get_filer_image()
        instance.large_screen_picture = get_filer_image()
        instance.small_screen_viewport_width = 12
        instance.medium_screen_viewport_width = 13
        instance.large_screen_viewport_width = 14

        self.assertEqual([
            AlternativePictureData(
                size_id=RESPONSIVE_IMAGES_BREAKPOINT_LARGE_ID,
                picture=instance.large_screen_picture,
                viewport_width=14,
                sizes_data=[
                    SizesAttributeData(1042, 14, []),
                ],
            ),
            AlternativePictureData(
                size_id=RESPONSIVE_IMAGES_BREAKPOINT_SMALL_ID,
                picture=instance.picture,
                viewport_width=12,
                sizes_data=[
                    SizesAttributeData(642, 13, []),
                    SizesAttributeData(0, 12, []),
                ],
            ),
        ], instance.alternative_pictures_data)

    def test_sources_formats(self):
        instance = self.picture
        self.assertEqual([("image/webp", "webp"), (None, None)], instance.sources_formats)
        instance.alternative_format_webp = ALTERNATIVE_FORMAT_WEBP_CHOICES[2][0]
        self.assertEqual([(None, None)], instance.sources_formats)

    def test_get_source_data(self):
        instance = self.picture
        # instance.medium_screen_picture = get_filer_image()
        # instance.large_screen_picture = get_filer_image()
        instance.small_screen_viewport_width = 12
        instance.medium_screen_viewport_width = 13
        instance.large_screen_viewport_width = 14

        version_data = AlternativePictureData(
            size_id=RESPONSIVE_IMAGES_BREAKPOINT_SMALL_ID,
            picture=instance.picture,
            viewport_width=12,
            sizes_data=[
                SizesAttributeData(1042, 14, []),
                SizesAttributeData(642, 13, []),
                SizesAttributeData(0, 12, [])
            ],
        )

        source_data = instance.get_source_data(version_data)

        self.assertEqual("", source_data.mime_type)
        self.assertEqual(version_data.picture, source_data.picture)
        self.assertEqual("(min-width: 1042px) 14vw, (min-width: 642px) 13vw, 12vw", source_data.sizes)
        self.assertEqual("", source_data.media)
        srcset_parts = source_data.srcset.split(", ")
        self.assertEqual(3, len(srcset_parts))

    def test_sources_data(self):
        instance = self.picture
        # instance.medium_screen_picture = get_filer_image()
        instance.large_screen_picture = get_filer_image()
        instance.small_screen_viewport_width = 12
        instance.medium_screen_viewport_width = 13
        instance.large_screen_viewport_width = 14

        sources_data = instance.sources_data
        self.assertEqual(3, len(sources_data))  # webp large, webp small, png large
        self.assertEqual(
            [
                ("image/webp", instance.large_screen_picture, '14vw',  '(min-width: 1042px)'),
                ("image/webp", instance.picture, '(min-width: 642px) 13vw, 12vw', ''),
                ("", instance.large_screen_picture, '14vw', '(min-width: 1042px)'),
            ],
            [(s.mime_type, s.picture, s.sizes, s.media) for s in sources_data]
        )

    def test_img_srcset(self):
        instance = self.picture
        self.assertEqual(3, len(instance.img_srcset.split(", ")))
        instance.use_responsive_image = USE_RESPONSIVE_IMAGE_CHOICES[2][0]
        self.assertIsNone(instance.img_srcset)

    def test_img_sizes(self):
        instance = self.picture
        self.assertEqual("(max-width: 542px) 542px, (max-width: 768px) 768px, 800px", instance.img_sizes)

        instance.small_screen_viewport_width = 12
        instance.medium_screen_viewport_width = 13
        instance.large_screen_viewport_width = 14
        self.assertEqual("(min-width: 1042px) 14vw, (min-width: 642px) 13vw, 12vw", instance.img_sizes)

        instance.use_responsive_image = USE_RESPONSIVE_IMAGE_CHOICES[2][0]
        self.assertIsNone(instance.img_sizes)
