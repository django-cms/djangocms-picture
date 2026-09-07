==========================
Migrating filer to finder
==========================

Install both contrib applications and back up the database and media storage.
First let django-finder create finder folders and inodes::

    python manage.py filer_to_finder public

Then audit djangocms-picture's deterministic reference mapping. The command uses
the UUID directory in each filer storage path, matching django-finder's migration::

    python manage.py migrate_picture_backend \
        --from filer --to finder --ambit public --dry-run \
        --audit-file picture-migration.jsonl

Each line is a JSON audit record. A row is only switched after its finder image
exists in the requested ambit. Apply the migration in bounded batches::

    python manage.py migrate_picture_backend \
        --from filer --to finder --ambit public --batch-size 250

Use ``--after-pk`` to resume after the last audited primary key and ``--limit``
for an operational window. The original filer ID is retained in the finder
reference's versioned configuration. This makes rollback independent of media
copying::

    python manage.py migrate_picture_backend \
        --from finder --to filer --ambit public --dry-run

    python manage.py migrate_picture_backend \
        --from finder --to filer --ambit public

Unified storage contains only the active source, so rollback replaces the finder
generic reference with the filer reference. The legacy
``--delete-finder-reference`` option is accepted as a no-op for scripting
compatibility. Skipped rows remain on their source backend. Errors are isolated
per row, reported in the audit, and make the command exit unsuccessfully after
later rows have been inspected.
