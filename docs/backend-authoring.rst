=========================
Writing a picture backend
=========================

A backend owns asset selection, identity, metadata and rendition generation. The
picture plugin owns presentation and portable transformation intent. Backend code
must live outside the core package; integrations shipped here use
``djangocms_picture.contrib.<name>``.

Registration
============

Register an alias, backend class and deployment-specific options::

    DJANGOCMS_PICTURE_BACKENDS = {
        "dam": {
            "BACKEND": "myproject.picture_backends.DamPictureBackend",
            "OPTIONS": {"library": "website"},
        },
    }

An integration with models, checks, admin registration or management commands
should also be a Django application in ``INSTALLED_APPS``. Backend classes are
loaded lazily from settings; core modules must not import provider SDKs.

Required contract
=================

Subclass ``BasePictureBackend`` and implement:

``serialize(value)``
    Convert a picker field's cleaned value into a ``PictureReference``.

``resolve(reference)``
    Resolve a reference into a ``BaseImageAsset`` without changing persistent
    state. Remote backends should normally resolve a stored snapshot so page
    rendering does not depend on provider availability.

``get_asset(instance)``
    Load the selected reference from the owning model or a typed one-to-one
    extension and return the resolved asset.

An asset exposes ``reference``, ``info``, ``get_original()`` and
``get_rendition(spec)``. Both rendition methods return a backend-neutral
``Rendition`` with URL and actual dimensions. Providers that require visible
credit expose an ``ImageAttribution`` through ``asset.attribution``; consuming
templates can render it where required. The shared type supports creator and
provider names and links, a copyright notice, and licence name and link. Use
``ImageAttribution.from_mapping()`` for external metadata so unsafe link schemes
are discarded consistently. Return ``None`` when the source has no trustworthy
credit metadata; do not infer authorship from a bare image URL.

Selection and persistence
=========================

``form_field()`` returns a normal Django field and provider picker widget. Its
cleaned value is deliberately native: a filer model, finder UUID, external URL,
or DAM payload. ``BackendImageField`` wraps configured backend fields and returns
a ``BackendSelection`` containing the backend instance and native value.

Implement ``set_form_value(instance, value, commit=False)`` to stage the native
value and persist it after the owner exists. Implement ``copy_reference`` for CMS
copy/paste and ``clear_reference`` when generic clearing is insufficient. Keep
provider-specific columns in a typed extension model. Do not add dynamic model
fields to ``Picture``.

Admin URLs
==========

A contrib app that needs an admin-side picker or API endpoint can register a
non-rendering system ``CMSPluginBase`` in its own ``cms_plugins.py`` and return
the backend-specific patterns from ``get_plugin_urls()``. Wrap views with
``admin.site.admin_view()``, and reverse their names through the ``admin``
namespace. The Unsplash contrib package provides a concrete example.

Capabilities
============

Declare ``BackendCapabilities`` truthfully. ``configuration_fields`` separately
lists portable form controls understood by the backend. The shared form uses both
to show and validate only applicable controls. In particular, do not advertise
``resize`` merely because a provider has a thumbnail API with fixed dimensions.

``resize``, ``crop`` and ``upscale`` describe ``RenditionSpec`` semantics;
``responsive`` permits multiple width candidates; ``presets`` supports portable
preset choices; ``upload`` and ``refresh`` advertise operational methods;
``remote`` marks a network-owned asset; ``permanent_urls`` says stored URLs do not
expire; and ``formats`` lists accepted output formats.

Data and security boundary
==========================

References contain asset identity and minimal render-safe context/snapshots.
Focal points, source dimensions, alt text, MIME type and provider revision are
source metadata. Display dimensions, crop intent, links, captions and HTML
attributes stay on the consuming model. Credentials, access tokens and arbitrary
picker metadata must never be serialized.

Remote adapters should allow-list HTTPS media hosts, normalize picker input,
define expiry behavior, refresh outside page rendering and use tombstones for
revoked assets. Permission or tenant context belongs in backend configuration or
the request, not in public URLs unless the provider requires a time-limited URL.

Serialized formats
==================

The public JSON formats are version 1::

    {
        "version": 1,
        "backend": "dam",
        "id": "asset-42",
        "context": {"library": "website"},
        "snapshot": {"label": "Hero", "width": 1600, "height": 900},
    }

    {
        "version": 1,
        "backend": "filer",
        "value": {"model": "filer.image", "pk": 42},
    }

``PictureReference.from_dict()`` and ``BackendSelection.deserialize()`` accept
unversioned dictionaries as legacy version 1. Unknown versions fail explicitly.
Django model values use django-entangled's ``{model, pk}`` convention. A
serialize/deserialize round trip must produce an equal object.

Verification checklist
======================

Test empty, stale and foreign references; picker validation; all advertised
rendition options; non-local storage; copy and clear hooks; provider deletion or
revocation; tenant/ambit boundaries; serialization round trips; admin media; and
real CMS plugin copy/paste. Run the backend against every supported Django and
django CMS combination, not only the newest pair.

See ``examples/standalone_backend_form.py`` for use outside a CMS plugin and the
shipped filer, finder, Frontify and Unsplash adapters for complete integrations.
