====================================
Proposed django-finder rendition API
====================================

Problem
=======

The finder branch currently exposes fixed thumbnails and low-level image-type
``crop()`` methods. A consumer must construct sample paths, coordinate storage,
infer actual dimensions and know which proxy model implements processing. That is
not a stable general resize contract, so djangocms-picture currently advertises
crop only.

Proposed public API
===================

django-finder could own two immutable provider-neutral values::

    @dataclass(frozen=True)
    class RenditionRequest:
        width: int | None = None
        height: int | None = None
        crop: bool = False
        upscale: bool = False
        format: str | None = None
        quality: int | None = None

    @dataclass(frozen=True)
    class RenditionResult:
        url: str
        width: int
        height: int
        path: str

and expose one method on image-capable file proxy models::

    image.get_rendition(ambit, request: RenditionRequest) -> RenditionResult

The method should validate unsupported combinations with a documented finder
exception. Width-only and height-only requests preserve aspect ratio. Two
dimensions with ``crop=False`` fit inside the box; with ``crop=True`` they fill
it using the stored focal region. ``upscale=False`` caps output at source size.
The returned dimensions describe the generated file, not requested dimensions.

Storage and caching semantics
=============================

Finder should derive a deterministic cache key from source inode, source revision
or SHA-1, normalized request and processing implementation version. It should use
the ambit's sample storage API exclusively, generate atomically under concurrent
requests, and never assume a local filesystem path. A regenerated source must not
reuse a stale rendition. SVG behavior should be explicit: either safe vector
resize/crop or a documented unsupported-operation error.

Capabilities and discovery
==========================

An image proxy should expose supported operations and formats so consumers can
configure their forms without importing PIL or SVG implementations. For example::

    image.rendition_capabilities(ambit) -> RenditionCapabilities

This can report resize, crop, upscale, formats and quality support. The API should
remain independent of django CMS and easy-thumbnails.

Required upstream tests
=======================

Tests should cover width-only, height-only, fit, crop/focal point, upscale caps,
format and quality validation, exact returned dimensions, cache reuse, source
revision invalidation, concurrent generation, non-filesystem storage, PIL and SVG
implementations, deleted sources and storage failures.

Adoption
========

Once released, ``FinderImageAsset.get_rendition()`` can become a thin translation
from djangocms-picture's ``RenditionSpec``. The adapter can then advertise resize,
upscale, responsive sources and formats based on finder capability discovery,
while existing finder references and picker behavior remain unchanged.
