import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from djangocms_picture.backends import get_backend
from djangocms_picture.contrib.frontify.backend import FrontifyPictureBackend
from djangocms_picture.contrib.frontify.models import FrontifyPictureReference


class Command(BaseCommand):
    help = "Refresh stored Frontify snapshots and disable references revoked by the provider."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--after-pk", type=int, default=0)
        parser.add_argument("--asset-id")
        parser.add_argument("--include-disabled", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        backend = get_backend("frontify")
        if not isinstance(backend, FrontifyPictureBackend) or not backend.capabilities.refresh:
            raise CommandError(
                'Configure DJANGOCMS_PICTURE_BACKENDS["frontify"]["OPTIONS"]["refresher"] first.'
            )
        if options["batch_size"] < 1:
            raise CommandError("--batch-size must be greater than zero.")

        queryset = FrontifyPictureReference.objects.select_related("picture_plugin").filter(
            pk__gt=options["after_pk"]
        )
        if options["asset_id"]:
            queryset = queryset.filter(asset_id=options["asset_id"])
        if not options["include_disabled"]:
            queryset = queryset.filter(disabled=False)

        counts = {"refreshed": 0, "would_refresh": 0, "revoked": 0, "error": 0}
        for extension in queryset.order_by("pk").iterator(chunk_size=options["batch_size"]):
            record: dict[str, Any] = {
                "event": "frontify_reference",
                "reference_pk": extension.pk,
                "picture_pk": extension.picture_plugin_id,
                "asset_id": extension.asset_id,
            }
            try:
                refreshed = backend.refresh_instance(
                    extension.picture_plugin,
                    commit=not options["dry_run"],
                )
                status = "would_refresh" if options["dry_run"] and refreshed else "refreshed"
                if refreshed is None:
                    status = "revoked"
            except Exception as error:  # Keep provider failures visible without losing later rows.
                status = "error"
                record["error"] = f"{type(error).__name__}: {error}"
            record["status"] = status
            counts[status] += 1
            self.stdout.write(json.dumps(record, sort_keys=True))

        self.stdout.write(json.dumps({"event": "summary", **counts}, sort_keys=True))
        if counts["error"]:
            raise CommandError(f'{counts["error"]} Frontify reference(s) could not be refreshed.')
