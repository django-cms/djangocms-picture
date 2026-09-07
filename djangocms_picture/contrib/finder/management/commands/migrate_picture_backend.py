import json
from collections.abc import Iterator
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from typing import Any, TextIO
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from finder.models.ambit import AmbitModel
from finder.models.file import FileModel

from djangocms_picture.backends import get_backend
from djangocms_picture.contrib.filer.backend import FilerPictureBackend
from djangocms_picture.contrib.finder.backend import FinderImageAsset, FinderPictureBackend
from djangocms_picture.models import Picture


class Command(BaseCommand):
    help = (
        "Switch djangocms-picture references between django-filer and django-finder after "
        "django-finder's filer_to_finder command has migrated the assets."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--from", dest="source", choices=("filer", "finder"), required=True)
        parser.add_argument("--to", dest="destination", choices=("filer", "finder"), required=True)
        parser.add_argument("--ambit", default="public", help="Finder ambit containing migrated images.")
        parser.add_argument("--dry-run", action="store_true", help="Audit without changing database rows.")
        parser.add_argument("--batch-size", type=int, default=250)
        parser.add_argument("--after-pk", type=int, default=0, help="Resume after this Picture primary key.")
        parser.add_argument("--limit", type=int, help="Process at most this many Picture rows.")
        parser.add_argument("--audit-file", type=Path, help="Also append JSON Lines audit records to this file.")
        parser.add_argument(
            "--delete-finder-reference",
            action="store_true",
            help="Deprecated compatibility option; unified storage always replaces the old reference.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        source = options["source"]
        destination = options["destination"]
        if source == destination:
            raise CommandError("--from and --to must name different backends.")
        if options["batch_size"] < 1:
            raise CommandError("--batch-size must be greater than zero.")
        if options["limit"] is not None and options["limit"] < 1:
            raise CommandError("--limit must be greater than zero.")

        try:
            finder_backend = get_backend("finder")
            filer_backend = get_backend("filer")
            if not isinstance(finder_backend, FinderPictureBackend):
                raise CommandError('The "finder" backend must be FinderPictureBackend.')
            if not isinstance(filer_backend, FilerPictureBackend):
                raise CommandError('The "filer" backend must be FilerPictureBackend.')
            ambit = AmbitModel.objects.get(slug=options["ambit"])
        except AmbitModel.DoesNotExist as error:
            raise CommandError(f'Finder ambit "{options["ambit"]}" does not exist.') from error

        audit_value = options["audit_file"]
        audit_file = Path(audit_value) if audit_value else None
        context = audit_file.open("a", encoding="utf-8") if audit_file else nullcontext(None)
        counts = {"migrated": 0, "would_migrate": 0, "skipped": 0, "error": 0}
        with context as audit_stream:
            for picture in self._pictures(options):
                record = self._migrate_picture(
                    picture,
                    source=source,
                    destination=destination,
                    ambit=ambit,
                    dry_run=options["dry_run"],
                    finder_backend=finder_backend,
                    filer_backend=filer_backend,
                )
                counts[record["status"]] += 1
                self._audit(record, audit_stream)
            self._audit({"event": "summary", **counts}, audit_stream)

        if counts["error"]:
            raise CommandError(
                f'{counts["error"]} picture reference(s) could not be migrated; use --after-pk to resume.'
            )

    @staticmethod
    def _pictures(options: dict[str, Any]) -> Iterator[Picture]:
        queryset = Picture.objects.filter(
            backend=options["source"],
            pk__gt=options["after_pk"],
        ).order_by("pk")
        if options["limit"] is not None:
            queryset = queryset[: options["limit"]]
        return queryset.iterator(chunk_size=options["batch_size"])

    def _migrate_picture(
        self,
        picture: Picture,
        *,
        source: str,
        destination: str,
        ambit: AmbitModel,
        dry_run: bool,
        finder_backend: FinderPictureBackend,
        filer_backend: FilerPictureBackend,
    ) -> dict[str, Any]:
        base = {
            "event": "picture",
            "picture_pk": picture.pk,
            "from": source,
            "to": destination,
            "ambit": ambit.slug,
        }
        try:
            if source == "filer":
                filer_image = picture.picture
                image = self._finder_image_for_filer(filer_image, ambit)
                if image is None:
                    return {**base, "status": "skipped", "reason": "finder image not found"}
                filer_id = getattr(filer_image, "pk", None)
                finder_id = str(image.pk)
                if not dry_run:
                    with transaction.atomic():
                        stored = finder_backend.prepare_storage(image)
                        if stored.reference is None:
                            raise ValueError("Finder did not accept the migrated image.")
                        reference = replace(
                            stored.reference,
                            context={
                                **stored.reference.context,
                                "legacy_filer_id": str(filer_id),
                            },
                        )
                        picture.backend = "finder"
                        picture.picture = stored.source_object
                        picture.picture_config = reference.as_dict()
                        picture.save(
                            update_fields=(
                                "backend",
                                "picture_content_type",
                                "picture_object_id",
                                "picture_config",
                            )
                        )
                return {
                    **base,
                    "status": "would_migrate" if dry_run else "migrated",
                    "filer_id": filer_id,
                    "finder_id": finder_id,
                }

            reference = finder_backend.get_stored_reference(picture)
            if reference is None:
                return {**base, "status": "skipped", "reason": "finder reference not found"}
            filer_id = reference.context.get("legacy_filer_id")
            if not filer_id:
                return {**base, "status": "skipped", "reason": "preserved filer reference not found"}
            try:
                filer_image = filer_backend.resolve(
                    replace(reference, backend="filer", id=str(filer_id), context={}, snapshot={})
                )
            except (TypeError, ValueError):
                filer_image = None
            if filer_image is None:
                return {**base, "status": "skipped", "reason": "preserved filer reference not found"}
            image = picture.picture
            if image and image.folder.get_ambit().pk != ambit.pk:
                return {**base, "status": "skipped", "reason": "finder image belongs to another ambit"}
            finder_id = str(getattr(image, "pk", image)) if image else None
            if not dry_run:
                with transaction.atomic():
                    filer_backend.set_form_value(picture, filer_image.image, commit=True)
            return {
                **base,
                "status": "would_migrate" if dry_run else "migrated",
                "filer_id": filer_id,
                "finder_id": finder_id,
            }
        except Exception as error:  # Keep each row independently resumable and auditable.
            return {**base, "status": "error", "error": f"{type(error).__name__}: {error}"}

    @staticmethod
    def _finder_image_for_filer(filer_image: Any, ambit: AmbitModel) -> Any | None:
        if filer_image is None:
            return None
        inode_id = UUID(Path(filer_image.file.name).parent.name)
        try:
            image = FileModel.objects.get_inode(
                id=inode_id,
                is_folder=False,
                mime_types=["image/*"],
            )
        except FileModel.DoesNotExist:
            return None
        return image if image.folder.get_ambit().pk == ambit.pk else None

    @staticmethod
    def _snapshot(image: Any) -> dict[str, Any]:
        return dict(FinderImageAsset(image).reference.snapshot)

    def _audit(self, record: dict[str, Any], stream: TextIO | None) -> None:
        line = json.dumps(record, sort_keys=True)
        self.stdout.write(line)
        if stream is not None:
            stream.write(f"{line}\n")
            stream.flush()
