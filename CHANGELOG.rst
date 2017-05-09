=========
Changelog
=========


2.0.5 (2017-05-09)
==================

* Fixed an issue in ``DJANGOCMS_PICTURE_ALIGN`` where "Align center" pointed to
  the wrong value
* Updated translations


2.0.4 (2016-11-22)
==================

* Prevent changes to ``DJANGOCMS_PICTURE_XXX`` settings from requiring new
  migrations
* Changed naming of ``Aldryn`` to ``Divio Cloud``
* Adapted testing infrastructure (tox/travis) to incorporate
  django CMS 3.4 and dropped 3.2
* Fixed an issue when no image is set after deletion in django-filer
  (on_delete=SET_NULL)
* Updated translations


2.0.3 (2016-10-31)
==================

* Fixed an issue with ``picture_link`` not working as expected in the template
* Fixed an issue where the alt text was not displayed appropriately
* Fixed an issue where placeholder params can be strings (#32)


2.0.2 (2016-09-20)
==================

* Fixed an issues with migrations where Null values caused ``IntegrityError``


2.0.1 (2016-09-13)
==================

* Fixes an issue where images throw an ``AttributeError``


2.0.0 (2016-09-08)
==================

* Backwards incompatible changes
    * Added ``DJANGOCMS_PICTURE_TEMPLATES`` setting
    * Added ``DJANGOCMS_PICTURE_NESTING`` setting
    * Added ``DJANGOCMS_PICTURE_ALIGN`` setting
    * Added ``DJANGOCMS_PICTURE_RATIO`` setting
    * Moved template from ``templates/cms/plugins/picture.html`` to
      ``templates/djangocms_picture/default/picture.html``
    * Renamed model field ``url`` to ``link_url`` and
      ``page_link`` to ``link_page``
    * Migrate model field ``image`` to ``FilerImageField``
      and renamed to ``picture``
    * Migrated ``alt`` and ``longdesc`` data to ``FilerImageField``
    * Renamed model field ``float`` to ``alignment``
    * Removed Django < 1.8 support
* Added adaptions to ``README.txt``
* Updated translations


1.0.0 (2016-04-03)
==================

* Use this version for Django < 1.8 support
