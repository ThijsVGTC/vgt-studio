from django.core.management.base import BaseCommand

from recordings.models import RecordingItem
from recordings.thumbnail_utils import (
    generate_thumbnail_for_item,
)


class Command(BaseCommand):

    help = "Genereer thumbnails voor oude video's"

    def add_arguments(self, parser):

        parser.add_argument(
            "--missing",
            action="store_true",
            help="Verwerk alleen items zonder thumbnail",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum aantal video's verwerken",
        )

    def handle(self, *args, **options):

        items = (
            RecordingItem.objects
            .exclude(old_video_url="")
            .order_by("id")
        )

        if options["missing"]:

            items = items.filter(
                thumbnail_path=""
            )

        if options["limit"]:

            items = items[:options["limit"]]

        processed = 0

        for item in items:

            self.stdout.write(
                f"Verwerken: "
                f"{item.signbank_id} - "
                f"{item.gloss_id}"
            )

            success, message = (
                generate_thumbnail_for_item(
                    item
                )
            )

            if success:

                processed += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {message}"
                    )
                )

            else:

                self.stdout.write(
                    self.style.ERROR(
                        f"  FOUT: {message}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Klaar. {processed} verwerkt."
            )
        )