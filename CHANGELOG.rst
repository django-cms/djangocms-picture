=========
Changelog
=========


2.0.4 (unreleased)
==================

* Prevent changes to ``DJANGOCMS_PICTURE_XXX`` settings from requiring new
  migrations
* Changed naming of ``Aldryn`` to ``Divio Cloud``
* Adapted testing infrastructure (tox/travis) to incorporate
  django CMS 3.4 and dropped 3.2


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
