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

The built-in ``filer`` and ``url`` aliases are enabled by default. Set either
entry to ``None`` to disable it. Aliases are stored on picture records and must
remain stable; migrate affected records before removing or renaming an alias.

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
    Load the selected reference from the picture plugin's generic object and
    JSON configuration and return the resolved asset.

An asset exposes ``reference``, ``info``, ``get_original()`` and
``get_rendition(spec)``. Both rendition methods return a backend-neutral
``Rendition`` with URL and actual dimensions. Providers that require visible
credit expose an ``ImageAttribution`` through ``asset.attribution``; consuming
templates must render it. The shared type supports creator and provider names
and links, a copyright notice, and licence name and link. Use
``ImageAttribution.from_mapping()`` for external metadata so unsafe link schemes
are discarded consistently. Return ``None`` when the source has no trustworthy
credit metadata; do not infer authorship from a bare image URL.

Selection and persistence
=========================

``form_field()`` returns a normal Django field and provider picker widget. Its
cleaned value is deliberately native: a filer model, finder UUID, external URL,
or DAM payload. ``BackendImageField`` wraps configured backend fields and returns
a ``BackendSelection`` containing the backend instance and native value.

The base backend serializes references into ``picture_config`` and implements
``set_form_value``, ``copy_reference`` and ``clear_reference``. Backends whose
picker returns a Django model override ``prepare_storage`` and return a
``StoredPictureSource`` containing both the serialized reference and model
object. Django stores that object through ``picture_content_type`` and the
textual ``picture_object_id``; textual IDs support integer, UUID and string
primary keys. Remote and URL backends leave the generic object empty.

``Picture.image_source`` is the virtual, typed interface to these backing
columns. Assigning a ``StoredPictureSource`` updates the backend alias, generic
model reference and JSON together. Reading it preserves the raw content type
and object ID even when the referenced object has been deleted, so copying a
plugin also preserves a useful tombstone. Backend implementations should not
assign the backing columns directly. The descriptor accepts custom backing
field names, so another image-consuming model can reuse the same storage value
without adopting ``Picture``'s column names.

The database constraint guarantees that content type and object ID are present
as a pair, and model validation checks that the serialized and generic IDs
match. A ``GenericForeignKey`` cannot create a database foreign-key constraint
to every possible target model, however. Deleting a referenced asset can
therefore leave a dangling object ID by design; rendering treats it as a
missing asset while the stored reference and snapshot remain available for
diagnostics, history and provider-specific recovery.

Override the persistence hooks only for additional lifecycle work. Backend JSON
must stay versioned and portable. Do not add provider-specific model fields or
one-to-one reference models to ``Picture``.

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

``picture_config`` contains a serialized ``PictureReference`` with asset
identity and minimal render-safe context/snapshots.
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
rendition options; integer or UUID generic object IDs where applicable;
non-local storage; copy and clear hooks; provider deletion or revocation;
tenant/ambit boundaries; serialization round trips; admin media; and real CMS
plugin copy/paste. Run the backend against every supported Django and django CMS
combination, not only the newest pair.

See ``examples/standalone_backend_form.py`` for use outside a CMS plugin and the
shipped filer, finder, Frontify and Unsplash adapters for complete integrations.
