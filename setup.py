#!/usr/bin/env python
from setuptools import find_packages, setup

from djangocms_picture import __version__


REQUIREMENTS = [
    'django-cms>=3.7',
    'django-filer>=1.7',
    'djangocms-attributes-field>=1',
    'easy_thumbnails',
]


CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Framework :: Django',
    'Framework :: Django :: 2.2',
    'Framework :: Django :: 3.0',
    'Framework :: Django :: 3.1',
    'Framework :: Django CMS',
    'Framework :: Django CMS :: 3.7',
    'Framework :: Django CMS :: 3.8',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    'Topic :: Software Development',
    'Topic :: Software Development :: Libraries',
]


setup(
    name='djangocms-picture',
    version=__version__,
    author='Divio AG',
    author_email='info@divio.ch',
    url='https://github.com/divio/djangocms-picture',
    license='BSD-3-Clause',
    description='Adds an image plugin to django CMS',
    long_description=open('README.rst').read(),
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIREMENTS,
    classifiers=CLASSIFIERS,
    test_suite='tests.settings.run',
)
