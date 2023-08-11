#!/usr/bin/env python
from pathlib import Path

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
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Framework :: Django',
    'Framework :: Django :: 3.2',
    'Framework :: Django :: 4.0',
    'Framework :: Django :: 4.1',
    'Framework :: Django :: 4.2',
    'Framework :: Django CMS',
    'Framework :: Django CMS :: 3.7',
    'Framework :: Django CMS :: 3.8',
    'Framework :: Django CMS :: 3.9',
    'Framework :: Django CMS :: 3.10',
    'Framework :: Django CMS :: 3.11',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    'Topic :: Software Development',
    'Topic :: Software Development :: Libraries',
]


this_directory = Path(__file__).parent
long_description = (this_directory / "README.rst").read_text()

setup(
    name='djangocms-picture',
    version=__version__,
    author='Divio AG',
    author_email='info@divio.ch',
    maintainer='Django CMS Association and contributors',
    maintainer_email='info@django-cms.org',
    url='https://github.com/django-cms/djangocms-picture',
    license='BSD-3-Clause',
    description='Adds an image plugin to django CMS',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIREMENTS,
    classifiers=CLASSIFIERS,
    test_suite='tests.settings.run',
)
