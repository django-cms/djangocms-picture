================
django CMS Image
================


|pypi| |build| |coverage|

**django CMS Image** is a plugin for `django CMS <http://django-cms.org>`_
that allows you to add images on your site.

This addon is compatible with `Aldryn <http://aldryn.com>`_ and is also available on the
`django CMS Marketplace <https://marketplace.django-cms.org/en/addons/browse/djangocms-image/>`_
for easy installation.

.. image:: preview.gif


Contributing
============

This is a an open-source project. We'll be delighted to receive your
feedback in the form of issues and pull requests. Before submitting your
pull request, please review our `contribution guidelines
<http://docs.django-cms.org/en/latest/contributing/index.html>`_.

One of the easiest contributions you can make is helping to translate this addon on
`Transifex <https://www.transifex.com/projects/p/djangocms-image/>`_.


Documentation
=============

See ``REQUIREMENTS`` in the `setup.py <https://github.com/divio/djangocms-image/blob/master/setup.py>`_
file for additional dependencies:

* Python 2.7, 3.3 or higher
* Django 1.8 or higher

Make sure `django Filer <http://django-filer.readthedocs.io/en/latest/installation.html>`_
is installed and configured appropriately.


Installation
------------

For a manual install:

* run ``pip install djangocms-image``
* add ``djangocms_image`` to your ``INSTALLED_APPS``
* run ``python manage.py migrate djangocms_image``


Configuration
-------------

You can override the alignment styles through the following setting:

    DJANGOCMS_IMAGE_ALIGN = [
        ('top', _('Top Aligned')),
    ]

This will generate a class prefixing "align-". The above written example
would result in ``class="align-top"``. Adding a ``class`` key to the image
attributes automatically merges the alignment with the attribute class.

Further configuration can be achieved through
`django Filer <https://django-filer.readthedocs.io/en/latest/settings.html>`_.


Running Tests
-------------

You can run tests by executing::

    virtualenv env
    source env/bin/activate
    pip install -r tests/requirements.txt
    python setup.py test


.. |pypi| image:: https://badge.fury.io/py/djangocms-image.svg
    :target: http://badge.fury.io/py/djangocms-image
.. |build| image:: https://travis-ci.org/divio/djangocms-image.svg?branch=master
    :target: https://travis-ci.org/divio/djangocms-image
.. |coverage| image:: https://codecov.io/gh/divio/djangocms-image/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/divio/djangocms-image
