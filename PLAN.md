# Plan: pluggable picture backends

## Decision summary

Implement the backend work incrementally around a small, public image-asset and rendition API.
Keep the existing `Picture` model, database table, plugin type, filer foreign key, thumbnail preset
field, settings, templates, and Python attributes working unchanged when no new setting is present.
The implicit and explicit default backend is `filer`.

Backend integrations live in contrib packages:

- `djangocms_picture.contrib.filer` is the default and adapts the current django-filer and
  easy-thumbnails behavior.
- `djangocms_picture.contrib.finder` adapts django-finder's UUID references, ambit-aware storage,
  picker, image metadata, and rendition generation.
- `djangocms_picture.contrib.frontify` is an example remote DAM adapter. It stores an opaque asset
  ID plus a render-safe metadata/URL snapshot, uses the Frontify picker, and maps Frontify's image
  processing URL parameters to the shared rendition contract.
- `djangocms_picture.contrib.url` is the built-in, original-only backend for the existing external
  URL input. It participates in the same selection UX and resolution API but has no managed asset,
  upload, crop, preset, responsive-rendition, or refresh capability.
- Future backends implement the same contracts without adding imports to the core package.

Do not try to hide the differences between an ORM foreign key and a finder UUID inside a dynamic
Django model field. The existing filer fields remain in place for compatibility. A small `backend`
column identifies how each plugin resolves its image, and a contrib backend may use a typed
one-to-one extension model for any additional persistence it needs. This preserves filer database
and Python compatibility while allowing old and new references to coexist during migration and
rollback.

Rendering and sizing must move out of the plugin model into backend-neutral services. This is the
main reusable seam for djangocms-frontend, whose image plugin currently duplicates picture sizing,
responsive source generation, thumbnail calls, missing-image handling, form selection, and upload
logic.

## Goals

1. Preserve the current django-filer experience by default, including existing rows, migrations,
   admin widgets, template overrides, rendition URLs, settings, and common Python access patterns.
2. Allow a project to select django-finder for new picture plugins and migrate existing references
   deliberately.
3. Allow more than one backend to be installed and allow old references to remain readable after
   the default changes.
4. Give templates and consumers one stable representation of image metadata and renditions.
5. Provide reusable selection, resolution, sizing, `srcset`, rendering, and upload APIs for
   djangocms-frontend and third-party plugins.
6. Keep storage SDKs, picker widgets, model classes, and thumbnail engines inside contrib packages.
7. Define contract tests which every backend must pass.
8. Support remote DAM systems which have no local Django asset model, may be temporarily
   unavailable, and may generate renditions by URL rather than by writing files.

## Non-goals for the first release

- Replacing django-filer's own models or admin.
- Managing arbitrary external URLs as uploaded assets. The existing `external_picture` value is
  exposed through the lightweight `url` backend, while remaining stored in its current column.
- Supporting arbitrary video or document files through the picture plugin.
- Removing the existing `picture` or `thumbnail_options` columns.
- Automatically changing every existing project from filer to finder.
- Making djangocms-picture depend on djangocms-frontend. Dependency direction must remain the other
  way around.
- Guaranteeing identical rendition filenames across different backends. The rendered dimensions
  and HTML contract matter; backend storage layouts do not.

## Research baseline

This plan is based on the repository state and the following upstream snapshots inspected on
2026-09-03:

- django-filer's `finder` branch at
  [`52e3294`](https://github.com/django-cms/django-filer/tree/52e32941365193764baa40ff71dbbf88a7264096).
- djangocms-frontend `main` at
  [`b78cb03`](https://github.com/django-cms/djangocms-frontend/tree/b78cb03baaae7d19e4b8cb36e04111bd3efad96a).
- django-frontify `master` at
  [`e6d3587`](https://github.com/lab360-ch/django-frontify/tree/e6d3587033d2e5fbc00dabf86520b4e177aaf172).
- The earlier djangocms-picture generic field spike in
  [PR #143](https://github.com/django-cms/djangocms-picture/pull/143).

## Implementation status

The first migration-free vertical slice is implemented:

- typed backend, image-asset, reference, capability, and rendition contracts;
- a lazy settings-based registry with `filer` as the default and `url` built in;
- filer and external-URL adapters over the existing fields;
- backend-neutral sizing, rendition, responsive-source helpers, and template tags;
- compatibility facades on `Picture`, with the default template no longer loading thumbnail tags;
- contract and characterization tests across the supported Django/django CMS matrix.

The second slice adds the per-row backend column, backend-defined picker and configuration fields,
capability-aware server-side forms, and matching dynamic admin behavior. Existing external URL
rows migrate to `url`; all other rows migrate to `filer`.

A first experimental finder backend draft now includes the typed UUID extension, finder picker,
ambit-aware resolution, original URLs, metadata snapshots, and focal crop generation. It is tested
separately against the pinned finder commit. Resize without crop, upscale, and responsive sources
remain disabled until finder exposes a public rendition API with those semantics.

The next increment adds full lifecycle hooks and system checks and hardens the finder draft for
copy/delete/migration workflows. The finder rendition API remains the first upstream dependency to
resolve before its adapter can be considered stable.

The finder branch is still under development. Its adapter must be tested against a pinned commit
until its public API is released, and assumptions listed below must be reconfirmed before the
finder contrib package is declared stable.

## Current coupling inventory

| Area | Current filer coupling | Required boundary |
| --- | --- | --- |
| Model reference | `FilerImageField` and integer `picture_id` | Backend-specific reference persistence and a neutral resolved asset |
| Presets | Foreign key to `filer.models.ThumbnailOption` | Optional backend capability plus portable rendition settings |
| Metadata | `label`, `default_alt_text`, `width`, `height`, `url`, `subject_location` | `ImageAsset` properties |
| Renditions | `easy_thumbnails.files.get_thumbnailer()` | `ImageAsset.get_rendition(spec)` |
| Responsive images | easy-thumbnails objects are returned and templates read `.url` | Neutral `Rendition` objects and a shared `srcset` builder |
| Form/admin | Widget is supplied by `FilerImageField` | Backend-provided form field/widget with a common clean value |
| Templates | `{% load thumbnail %}` and backend-shaped values | Core tags and/or precomputed render data only |
| Copy/delete | Foreign-key behavior and direct assignment to `picture` | Backend hooks for copy, clear, validation, and reference lifecycle |
| Tests | Filer model factories and thumbnail path assertions | Shared backend contract tests plus adapter-specific integration tests |
| Packaging | Hard imports and dependencies on filer/easy-thumbnails | Imports and optional dependencies isolated in contrib packages |
| Migrations | Historical migrations import filer fields and models | Leave history intact; add forward-only neutral/backend extension migrations |
| Availability | Local model/storage is assumed available during rendering | Snapshot-first resolution and explicit refresh behavior for remote DAMs |

Additional djangocms-frontend coupling to replace:

- `AdminImageFormField`, `FilerImageField`, `filer.models.Image`, and `ThumbnailOption` in its image
  form.
- `{model, pk}` filer references in `FrontendUIItem.config` and `get_related_object()`.
- Direct easy-thumbnails calls in `ImageMixin`, `img_src`, and `img_srcset_data`.
- Filer-specific upload code in `contrib/image/image_save.py`.
- Template access to `rel_image.default_alt_text` and thumbnail `.url`.

## Target package layout

```text
djangocms_picture/
    backends/
        __init__.py          # registry and get_backend()
        base.py              # protocols/base classes and exceptions
        types.py             # PictureReference, ImageInfo, RenditionSpec, Rendition
        checks.py            # Django system checks
    fields.py                # reusable form facade; no backend SDK imports
    forms.py                 # backend-neutral PictureForm orchestration
    rendering.py             # sizing, srcset and render-data builder
    templatetags/
        djangocms_picture.py # stable tags delegating to rendering.py
    contrib/
        filer/
            apps.py
            backend.py
            fields.py
            forms.py
            rendering.py
        finder/
            apps.py
            backend.py
            fields.py
            forms.py
            models.py        # typed extension/reference model
            rendering.py
            migrations/
        frontify/
            apps.py
            backend.py
            fields.py
            forms.py
            models.py        # opaque ID and persisted asset snapshot
            rendering.py     # Frontify processing-URL translation
            migrations/
```

Contrib modules must be lazy-loaded. Importing `djangocms_picture.backends`, `fields`, or
`rendering` must not import `filer`, `easy_thumbnails`, or `finder`. Django system checks should
produce actionable errors when a configured backend's dependency or app is missing.

Initially both contrib packages can ship in the djangocms-picture wheel, selected through extras
and settings. If maintenance or dependency release cycles diverge, the same contracts allow later
extraction into separately versioned distributions without changing consumers.

## Core contracts

The exact names may change during the contract spike, but the responsibilities should not.

### Data ownership

Keep transformation intent separate from provider data:

| Data | Owner | Examples |
|---|---|---|
| Backend choice | Core plugin row | `filer`, `finder`, `url`, `frontify` |
| Presentation | Core plugin row | caption, alignment, link, HTML attributes, display width/height |
| Portable transformation intent | Core plugin row/render request | automatic sizing, original, crop, upscale, responsive sources, portable preset slug |
| Asset identity | Backend reference/extension | filer PK, finder UUID and ambit, Frontify asset ID and account/library alias, external URL |
| Source metadata | Backend reference/extension snapshot | intrinsic dimensions, MIME type, title, alt text, focal point, copyright/licence, revision |
| Rendition implementation | Backend adapter | easy-thumbnails options, finder samples, Frontify processing URL parameters |
| Provider operations | Backend adapter | picker, upload, refresh, permissions, health checks, tombstones |
| Credentials | Deployment settings/secrets manager | API keys, OAuth secrets and account credentials; never plugin/reference data |

Crop and resize settings therefore do not become filer/finder/Frontify model fields. They remain a
portable request understood by all consumers, while each backend declares whether it supports
`resize`, `crop`, `upscale`, `responsive`, `presets`, `upload`, and `refresh`. Asset-specific focal
points belong to backend metadata because they describe the selected source, not the plugin's
rendering choice. A provider-specific crop identifier or URL recipe may live in the backend
snapshot, but templates only receive the normalized rendition result.

The edit form uses these declarations in two layers:

- `selection_field_name` selects the backend-owned picker/input (`picture`, `external_picture`, a
  finder picker, or a DAM picker);
- `configuration_fields` lists the portable plugin controls that backend supports.

JavaScript switches the visible picker and enabled controls immediately. The bound Django form
derives the same state from submitted `backend`, disables unsupported values server-side, and
requires the selected backend's picker value. Thus the browser behavior is progressive enhancement,
not the security or validation boundary.

```python
@dataclass(frozen=True)
class PictureReference:
    backend: str
    id: str
    context: Mapping[str, JSONValue] = field(default_factory=dict)
    snapshot: Mapping[str, JSONValue] = field(default_factory=dict)


@dataclass(frozen=True)
class ImageInfo:
    label: str
    width: int | None
    height: int | None
    alt_text: str = ""


@dataclass(frozen=True)
class RenditionSpec:
    width: int | None = None
    height: int | None = None
    crop: bool = False
    upscale: bool = False
    format: str | None = None
    quality: int | None = None


@dataclass(frozen=True)
class Rendition:
    url: str
    width: int | None
    height: int | None


class ImageAsset(Protocol):
    reference: PictureReference
    info: ImageInfo

    def get_original(self) -> Rendition: ...
    def get_rendition(self, spec: RenditionSpec) -> Rendition: ...


class PictureBackend(Protocol):
    alias: str

    def form_field(self, *, required: bool, request=None, **kwargs): ...
    def serialize(self, value) -> PictureReference | None: ...
    def resolve(self, reference: PictureReference) -> ImageAsset | None: ...
    def get_reference(self, picture_instance) -> PictureReference | None: ...
    def set_reference(self, picture_instance, reference, *, commit: bool): ...
    def copy_reference(self, source, target): ...
    def clear_reference(self, picture_instance): ...
    def upload(self, file, *, name: str, user=None, context=None) -> PictureReference: ...
    def refresh(self, reference: PictureReference, *, request=None) -> PictureReference: ...
```

Contract details:

- IDs are serialized as strings so integer filer primary keys and finder UUIDs have one portable
  JSON representation.
- Backend-specific, non-secret routing information such as a finder ambit or configured DAM account
  alias belongs in `context`; it must not leak into templates or sizing code.
- `snapshot` contains only persisted, render-safe values needed when the authoritative backend is
  not queried: dimensions, label, alt metadata, revision, and stable rendition/original URL data.
  It must never contain OAuth tokens, API keys, signed short-lived credentials, or unrestricted raw
  picker payloads.
- `resolve()` returns `None` for a missing/deleted reference. Normal page rendering must not raise
  an object lookup exception or synchronously call a remote provider. A remote backend resolves
  from its persisted snapshot/cache; `refresh()` is an explicit admin, command, webhook, or
  background operation.
- A `Rendition` is deliberately smaller than an easy-thumbnails object. Consumers only rely on its
  URL and actual dimensions.
- `RenditionSpec` describes intent. Unsupported options must have documented deterministic
  behavior: either a capability error during validation or an explicit fallback, never silent
  backend-dependent interpretation.
- Backends may expose capabilities such as `presets`, `crop`, `upscale`, `svg`, and `upload` so the
  form hides unsupported controls and validates existing values.
- Capabilities must also cover `remote`, `refresh`, `upload`, `permanent_urls`, and supported output
  formats. Remote picker-only systems are valid backends even when `upload()` is unsupported.
- Public rendering must not depend on the current request user. Selection enforces editor
  permissions; rendition URLs must follow the selected ambit's/public storage policy so cached CMS
  output cannot leak private assets.

## Persistence and backwards compatibility

### Existing filer data

Keep these pieces unchanged:

- `djangocms_picture.Picture` and its database table.
- The `picture` `FilerImageField`, `picture_id`, and normal filer deletion behavior.
- The `thumbnail_options` foreign key.
- The `PicturePlugin` class name/plugin type.
- Existing template names, settings, model methods, and context keys.

Add a `backend` `CharField`, hidden from the default form, with a data migration setting every
existing row to `filer`. If the column is absent from old serialized plugin data, the runtime
fallback is also `filer`. Changing `DJANGOCMS_PICTURE_DEFAULT_BACKEND` affects new selections only;
it never changes how an existing row is resolved.

The new `instance.image` or `instance.image_asset` property returns the neutral `ImageAsset`.
Existing filer projects retain `instance.picture` as the actual filer image. Existing helper
properties (`img_src`, `img_srcset_data`, `get_size`, and `get_short_description`) remain as
compatibility facades over the new rendering service.

### External URL references

Treat the current external image input as a built-in `url` backend from the selection and rendering
UX. Keep `external_picture` unchanged and preserve its precedence over a retained filer reference.
The backend serializes the URL itself as the opaque ID and may snapshot explicitly configured
dimensions and alt text; it performs no network lookup while rendering. Its only rendition is the
original URL, and its capabilities explicitly disable uploads, crop, upscale, presets, responsive
sources, and refresh. This makes URL behavior consistent with managed backends without pretending
that djangocms-picture owns or can transform the resource.

### Finder references

The finder contrib app adds a model similar to:

```python
class FinderPictureReference(models.Model):
    picture_plugin = models.OneToOneField(
        "djangocms_picture.Picture",
        related_name="finder_reference",
        on_delete=models.CASCADE,
    )
    image = FinderFileField(
        accept_mime_types=["image/*"],
        on_delete=models.SET_NULL,
        null=True,
        ambit=...,  # picker default; the resolved inode can find its actual ambit
    )
```

This keeps UUID typing and finder deletion handling inside a Django app loaded only when finder is
installed. New finder-backed plugin rows leave the legacy filer `picture` column null. The backend
hook creates/updates the extension after the CMS plugin has a primary key and clones it from
`copy_relations()`.

Do not use a GenericForeignKey as the primary solution. Content types identify a Django model but
do not describe an ambit, picker, rendition engine, or backend capabilities. They also weaken
database deletion behavior, complicate mixed integer/UUID validation, and would still require most
of the backend contract above. PR #143 remains useful as a form-field experiment, not as the
storage architecture.

Do not dynamically change the concrete type of one model field from an integer foreign key to a
UUID field based on settings. That makes migration state and database schemas depend on runtime
configuration and makes backend changes unsafe.

Remote contrib packages use the same extension pattern with storage appropriate to the provider.
For example, a Frontify extension stores `asset_id`, a configured account/library alias, a
normalized JSON snapshot, and optional provider revision/refresh timestamps. It does not need a
foreign key to a local asset model.

### Migration from filer to finder

Add a management command with dry-run, batching, resume, and audit output, for example:

```console
python manage.py migrate_picture_backend \
    --from filer --to finder --ambit public --dry-run
```

The finder branch's `filer_to_finder` command derives finder UUIDs from the parent directory of a
filer file's stored path. The picture migration should use the finder command's public mapping API
if one exists by implementation time; otherwise share/extract that mapping rather than duplicating
it silently.

For rollback safety, migration initially creates the finder extension and switches `backend` but
does not clear `picture_id`. A separate explicit cleanup operation may remove legacy references
after verification. Log unmapped files, missing payloads, unsupported MIME types, inaccessible
ambits, and duplicate mappings. Never change external-image-only plugins.

## Rendering and template abstraction

Move size calculation, option normalization, alt-text precedence, missing-image behavior, and
responsive breakpoint selection into `djangocms_picture.rendering` as pure functions/services.
Inputs should be an `ImageAsset` plus backend-neutral options; outputs should be a
`PictureRenderData` value containing at least:

- `src`, `width`, `height`, and `alt`;
- normalized HTML attributes;
- zero or more `{url, width}` `srcset` candidates;
- the final `sizes` value;
- optional link/caption data where useful to the standalone plugin.

The default template should consume render data and must not load `thumbnail` or `finder_tags`.
Keep today's context variables (`picture_link`, `picture_size`, and `img_srcset_data`) for custom
template compatibility during a deprecation period, but make them backend-neutral objects.

Provide a stable core template-tag library for use outside the CMS plugin. Initial API candidates:

```django
{% load djangocms_picture %}
{% picture_rendition image width=640 height=360 crop=True as rendition %}
{% picture_srcset image widths="320,640,960" crop=False as sources %}
{% render_picture image width=640 alt="Example" %}
```

The tags only normalize arguments and call the core rendering service. They must never import a
backend implementation directly. Final tag signatures should be selected after testing them in
both djangocms-picture templates and a standalone model/template example.

Responsive generation must use each rendition's actual output width for the `w` descriptor, avoid
duplicates, sort candidates, omit widths larger than the useful original unless upscaling is
explicit, and tolerate a candidate that cannot be generated.

## Filer contrib implementation

The first implementation is a behavior-preserving extraction:

- Reference: existing `instance.picture` / `picture_id`.
- Picker: existing `FilerImageField`/admin widget.
- Metadata: map `label`, `default_alt_text`, `width`, `height`, `url`, and `subject_location`.
- Original: current `picture.url` behavior.
- Rendition: wrap `get_thumbnailer(...).get_thumbnail(...)` and translate `RenditionSpec` into the
  current easy-thumbnails options.
- Presets: continue honoring `ThumbnailOption` exactly as today.
- Copy/delete: retain the current FK and `copy_relations()` semantics.
- Exceptions: translate missing files and easy-thumbnails `ValueError` into an absent asset or
  rendition result as appropriate.

Before adding finder behavior, run characterization tests against the current filer implementation.
Capture HTML, form widgets/media, model attribute behavior, external-image precedence, crop/upscale
options, presets, responsive breakpoints, custom templates, plugin copying, deleted images, and
migrations from the last released version. Refactoring to the filer adapter passes only when these
tests remain unchanged.

## Finder contrib implementation

The finder adapter maps:

- `FinderFileField(accept_mime_types=["image/*"])` to selection and typed reference persistence.
- `ImageFileModel.name`, `width`, `height`, and `meta_data["alt_text"]` to `ImageInfo`.
- `file.get_ambit()` plus `get_download_url(ambit)` to the original rendition.
- Finder's sample storage and image model to generated renditions.
- The configured default ambit to the picker; the selected file's actual ambit remains authoritative
  while rendering.

There is an upstream API gap to resolve before implementation. At the inspected commit finder only
documents a fixed-size `get_thumbnail_url()` and a low-level `crop(ambit, path, width, height)`;
its own documentation says there is no template-level arbitrary rendition API. djangocms-picture
needs a public finder API which supports:

- resize without crop;
- crop with art direction/focal data;
- explicit upscale behavior;
- deterministic filenames containing every transformation input;
- the actual output dimensions;
- safe lazy generation in original/sample storage;
- PIL raster images and SVG, with defined behavior for unmeasurable SVGs;
- concurrent first requests without corrupt/partial samples.

Prefer adding this API upstream to finder and making the contrib adapter thin. If that cannot land
first, isolate the temporary implementation entirely in `contrib.finder.rendering` and treat it as
provisional.

Finder-specific tests must cover ambit selection, read permissions in the picker, public URL policy,
PIL and SVG images, focal crops, missing dimensions, deleted/trash files, reference `SET_NULL`,
plugin copy/paste, storage backends without local paths, and concurrent rendition requests.

## Remote DAM contrib implementation: Frontify

Frontify validates that a backend cannot be modeled only as a local Django file field. The inspected
django-frontify package:

- provides a JavaScript Frontify Finder picker;
- persists the selected asset's JSON response in a text-backed model field;
- reconstructs a lightweight `FrontifyImage` without a server API lookup;
- maps width, height, format, quality, and focal-point crop options to query parameters on a stable
  asset URL;
- supports metadata-driven, language-specific alt text;
- does not provide a local asset model or database foreign key.

Add Frontify as a third contract implementation after the core contract is stable. The contrib app
may initially depend on and adapt `django-frontify`, but no `django_frontify` import may escape the
contrib package. Before choosing that dependency, verify its Django/Python support and the current
Frontify Finder/API version; the inspected repository snapshot dates from 2024 and targets older
Django/django CMS releases.

The Frontify adapter should:

- use a typed extension row containing the CMS plugin relation, opaque Frontify asset ID, configured
  account/library alias, normalized snapshot JSON, provider revision, and refreshed-at timestamp;
- reuse or modernize the Frontify Finder widget while preserving its admin media through the shared
  `PictureFormField` contract;
- normalize title/name, dimensions, alt metadata, preview/original URL data, supported formats, and
  focal point into `ImageInfo`/snapshot values;
- build rendition URLs from `RenditionSpec` without calling Frontify while a permanent processing
  base URL is available;
- reject or explicitly approximate unsupported options such as upscale rather than silently
  changing semantics;
- expose `upload=False` unless a separate authenticated upload workflow is implemented;
- implement `refresh()` through the current Frontify API or picker payload, with timeouts, retries,
  rate-limit handling, and an audit trail;
- keep the last known-good snapshot renderable during provider outages;
- support explicit tombstone/disabled state when a webhook or refresh confirms that an asset is
  deleted or no longer licensed;
- sanitize and allow-list all persisted URL schemes/hosts and all metadata rendered into HTML.

Do not store Frontify client secrets, OAuth access tokens, browser local-storage tokens, or expiring
signed URLs in plugin rows. Account aliases resolve credentials from settings or a secrets manager.
If Frontify cannot provide permanent rendition URLs, define a refresh/proxy/CDN strategy before the
adapter is production-ready; server-side network access during every page render is not acceptable.

The current django-frontify widget loads third-party JavaScript from a public CDN. The contrib
package should prefer a pinned, bundled asset or make the external origin/version explicit so sites
can configure Content Security Policy and supply-chain controls.

Frontify-specific tests must cover picker payload versions, snapshot normalization, localized alt
metadata, rendition parameter encoding, supported output formats, malformed/untrusted URLs,
permanent versus expiring URLs, stale snapshots, provider timeouts/rate limits, deleted assets,
webhook refresh, and rendering while the provider is unavailable. HTTP tests use recorded/synthetic
responses; the normal unit/CI suite must not require Frontify credentials.

## Portable presets

`ThumbnailOption` is a filer database model and cannot be the shared preset abstraction.

For the initial release:

- Preserve `thumbnail_options` for filer records and forms.
- Treat presets as an optional backend capability.
- For finder, expose ordinary width/height/crop/upscale controls first rather than pretending a
  filer preset exists.

Then introduce a backend-neutral setting such as `DJANGOCMS_PICTURE_RENDITION_PRESETS`, keyed by a
stable slug and containing `RenditionSpec` values. Store the selected slug in a new neutral field.
The filer adapter may translate legacy `ThumbnailOption` rows into specs at render time. A later
data migration can map named filer presets to portable slugs, but must report ambiguous or missing
matches.

## Settings and registration

Proposed configuration:

```python
DJANGOCMS_PICTURE_BACKENDS = {
    "filer": {
        "BACKEND": "djangocms_picture.contrib.filer.backend.FilerPictureBackend",
    },
    "finder": {
        "BACKEND": "djangocms_picture.contrib.finder.backend.FinderPictureBackend",
        "OPTIONS": {"ambit": "public"},
    },
    "frontify": {
        "BACKEND": "djangocms_picture.contrib.frontify.backend.FrontifyPictureBackend",
        "OPTIONS": {"account": "brand-library"},
    },
}
DJANGOCMS_PICTURE_DEFAULT_BACKEND = "filer"
```

With no settings, register `filer` and behave exactly as the current release. Validate aliases,
import paths, required apps, unique registration, backend contract version, default ambit, and
storage availability with Django system checks. Cache backend instances only after Django's app
registry is ready and provide a test-only cache reset.

The admin may initially expose only the configured default backend for new selections. Supporting a
visible per-plugin backend chooser is a separate product decision; the persistence model must not
prevent it.

## Reuse by djangocms-frontend

Build the shared API without depending on either plugin model:

1. `PictureReference`, `ImageAsset`, `RenditionSpec`, `Rendition`, and the rendering service are
   plain Python contracts.
2. `PictureFormField` delegates selection to a configured backend and cleans to a serializable
   `PictureReference`.
3. Reference serialization reads both the new `{backend, id, context, snapshot}` shape and the current
   djangocms-frontend `{model, pk}` filer shape. Writes use only the new versioned shape.
4. djangocms-frontend's `ImageMixin` becomes a thin consumer of the shared sizing/rendering service.
   Bootstrap-specific classes, margins, links, lazy loading, and its entangled JSON model remain in
   djangocms-frontend.
5. Its form uses the shared backend-aware selection field. Filer-only `ThumbnailOption` UI remains
   available through capabilities until portable presets replace it.
6. Its drag-and-drop `create_image_plugin()` calls `backend.upload()` and serializes the returned
   reference instead of constructing a filer model directly.
7. Its image template consumes neutral render data and no longer loads `thumbnail` or reads
   `rel_image.default_alt_text`.

Create a small consumer contract test package in djangocms-picture that djangocms-frontend can run
against its supported djangocms-picture range. Coordinate the actual frontend conversion as a
separate pull request after the filer adapter API is released; do not couple the two repositories
through imports of private modules.

## Reusable fields for third-party models

Offer a stable `PictureFormField` in the first release. For ORM models, expose backend-specific
typed fields (`FilerPictureField`, `FinderPictureField`, and a snapshot-backed
`FrontifyPictureField`) and a documented renderer that accepts their cleaned values.

Only add a convenience `PictureField(backend="...")` factory after a migration prototype proves
that `deconstruct()` always serializes the explicit backend alias and produces deterministic
migration state. Never let the default backend setting silently change the database type of an
already-migrated third-party field.

Provide a minimal example app showing:

- a regular Django model with each typed field;
- the common form/picker behavior;
- `{% render_picture %}` usage;
- safe behavior for missing/deleted assets.

## Delivery phases

### Phase 0: contracts and compatibility characterization

- Freeze the public behavior of the current filer plugin in tests.
- Prototype the contracts with fake in-memory and filer implementations.
- Decide names and version the reference serialization format.
- Prototype finder resize/crop generation and agree on the upstream finder API.
- Prove the extension-model migration and CMS plugin copy flow.
- Document the supported meaning of crop, upscale, original, dimensions, and alt text.

Exit criterion: the interfaces can render the same fixture through fake, filer, finder, and remote
DAM assets, and the persistence prototype migrates/rolls back without changing the CMS plugin
identity.

### Phase 1: extract the default filer backend

- Add registry, contracts, render data, and system checks.
- Move filer imports and thumbnail behavior into `contrib.filer`.
- Add the `backend` column/data migration with `filer` default.
- Turn existing model helpers into compatibility facades.
- Replace the default template's backend-shaped inputs while retaining old context keys.
- Add core template tags and standalone examples.
- Publish the public consumer API and deprecation policy.

Exit criterion: the full old filer test suite and migration tests pass without new settings, and
rendered output/form behavior is unchanged except for explicitly documented bug fixes.

### Phase 2: add the finder backend

- Add optional dependency/installation documentation and the contrib Django app.
- Add the typed finder extension model and form orchestration.
- Implement metadata, original URL, rendition, srcset, upload, copy, clear, and missing-reference
  behavior.
- Add the filer-to-finder picture migration command and rollback workflow.
- Add finder contract/integration tests and CI against a pinned finder commit.
- Mark finder experimental until its upstream rendition API is released.

Exit criterion: users can create, edit, copy, publish, render, delete, and migrate picture plugins
with finder on every supported Django/django CMS version and configured storage type.

### Phase 2b: prove the remote DAM contract with Frontify

- Add the Frontify extension model, picker adapter, safe snapshot normalizer, and rendition URL
  translator.
- Add explicit refresh/health workflows and last-known-good behavior without network calls during
  normal rendering.
- Add credential/account configuration, URL allow-listing, CSP documentation, and mocked provider
  tests.
- Decide whether to depend on a modernized django-frontify package or implement a maintained
  adapter directly in the contrib package.

Exit criterion: selecting and rendering a Frontify image exercises the same public form and
rendering contracts as filer/finder, and published pages remain renderable during a simulated
Frontify outage without exposing credentials or stale signed URLs.

### Phase 3: djangocms-frontend adoption

- Release the shared API from djangocms-picture.
- Convert frontend's form, model mixin, rendering, template, and upload handler.
- Add compatibility reading for existing `{model, pk}` config values and a management command or
  lazy rewrite path for the new reference shape.
- Run cross-repository consumer contract tests for filer, finder, and Frontify.

Exit criterion: djangocms-frontend contains no direct easy-thumbnails/filer code in its image
rendering path, while its Bootstrap behavior and existing stored configurations remain compatible.

### Phase 4: optional dependency cleanup

- After at least one deprecation cycle, assess whether the historical filer migrations and legacy
  columns should remain indefinitely or move to a separately versioned filer contrib distribution.
- If splitting distributions, publish a migration/install path that keeps historical migrations
  importable and never strands existing projects.
- Consider removing the hard django-filer dependency only in a major release.

## Test and CI plan

Run the same backend contract suite for every adapter. It should test:

- reference serialization round trips and invalid reference handling;
- selection field/widget media and validation;
- metadata normalization and alt-text precedence;
- original, resize, crop, upscale, responsive candidates, and actual dimensions;
- external URL precedence;
- missing/deleted/trash assets;
- copy and clear lifecycle hooks;
- public URL/security policy;
- non-local Django storage;
- template tags and `PictureRenderData` output.

CI layers:

1. Core unit tests with a fake backend, no filer/finder imports.
2. Filer characterization and integration tests across the supported Django/django CMS matrix.
3. Finder integration tests across the same applicable matrix, initially pinned to an upstream
   commit and allowed to run as an experimental job only until the contract stabilizes.
4. Frontify adapter tests with synthetic/recorded responses, including an offline render job. Live
   credentialed smoke tests, if added, run separately and are never required for pull requests.
5. Migration tests from the last released djangocms-picture database state.
6. A lightweight djangocms-frontend consumer fixture, plus full cross-repository tests in the
   frontend repository.
7. Packaging tests for default install, each contrib backend independently, multiple backends
   installed, missing configured dependencies, and import of core modules without optional
   packages.

## Documentation deliverables

- Backend author guide with the complete contract and capability semantics.
- Filer and finder installation/configuration guides.
- Remote DAM/Frontify configuration, credential, refresh, CSP, and outage-behavior guide.
- Backend migration and rollback runbook.
- Template-tag and standalone-model examples.
- djangocms-frontend integration guide.
- Compatibility/deprecation table for model attributes, settings, templates, context variables,
  and serialized references.
- Security note explaining picker permissions versus publicly renderable URLs.

## Open decisions and risks

1. **Finder rendition API:** coordinate upstream before freezing the adapter. Its current
   `get_thumbnail_url()` is fixed at 180 px and `crop()` is too low-level for this contract.
2. **Backend selection UX:** decide whether selection is project-wide, per site/placeholder, or
   visible per plugin. Persistence should support per-row aliases regardless.
3. **Portable presets:** agree on settings-based preset schema and migration rules before exposing
   finder presets.
4. **Finder branch packaging:** confirm its eventual distribution name, supported versions, and
   whether legacy `filer` modules remain included.
5. **Public/private ambits:** define which ambits may be rendered on public pages and how private
   storage URLs are signed without making cached HTML user-specific.
6. **SVG behavior:** define whether SVG is served as original, rewritten for dimensions, or
   rasterized for each requested rendition.
7. **Cache invalidation:** ensure rendition keys include source revision/hash and all spec/focal
   inputs; define cleanup of unreferenced samples.
8. **Concurrent generation:** require atomic writes or locking for the first rendition request.
9. **Legacy dependency removal:** full default compatibility conflicts with immediately removing
   filer imports from historical migrations. Treat that as a later major-version packaging task.
10. **Remote asset freshness:** define snapshot TTLs, webhook handling, manual refresh, failure
    backoff, and what editors see when a DAM asset is revoked.
11. **Remote URL lifetime:** require permanent URLs or an explicit CDN/proxy refresh design; never
    persist credentials or assume a signed URL lives forever.
12. **Provider metadata mapping:** alt text, copyright, licensing, locale, and focal-point schemas
    vary by account. Keep mapping configurable and preserve unmapped safe metadata for future
    refreshes.

## Definition of done

- An unconfigured upgraded project behaves as a filer-backed project and passes migration and HTML
  characterization tests.
- Filer and finder can coexist; changing the default does not reinterpret existing rows.
- No core rendering, form orchestration, or template imports a backend SDK.
- Filer, finder, and the reference remote-DAM adapter pass the same applicable contract suite;
  unsupported capabilities are explicit and tested.
- Finder supports arbitrary requested dimensions for original/resize/crop and responsive output.
- Plugin copy, deletion, missing references, external URLs, and rollback are covered.
- The public APIs used by djangocms-frontend are documented, versioned, and tested as consumer
  contracts.
- A regular Django model can select and render an image through documented fields/forms/template
  tags without depending on a CMS plugin model.
- A published page backed by a remote DAM renders from a safe last-known-good snapshot without a
  provider API call, and has an explicit refresh/revocation path.
