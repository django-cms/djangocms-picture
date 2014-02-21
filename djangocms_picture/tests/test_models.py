from django.test import TestCase
from django.utils.html import escapejs
from ..models import Picture


class PictureTestCase(TestCase):
    def test_escapejs_does_not_break_on_empty_picture(self):
        """A Picture object can be passed to Django's escapejs"""
        pic = Picture()
        try:
            escapejs(pic)
        except TypeError:
            self.fail("escapejs() raised TypeError on empty picture!")
