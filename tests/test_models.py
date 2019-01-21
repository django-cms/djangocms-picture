# -*- coding: utf-8 -*-
from django.test import TestCase

from djangocms_picture.models import Picture

EXAMPLE_IMAGE = 'https://www.google.com/images/logo.png'


class PictureTestCase(TestCase):

    def setUp(self):
        Picture.objects.create(
            external_picture=EXAMPLE_IMAGE,
        )

    def test_picture_instance(self):
        """Picture instance has been created"""
        picture = Picture.objects.get(external_picture=EXAMPLE_IMAGE)
        self.assertEqual(picture.external_picture, EXAMPLE_IMAGE)
