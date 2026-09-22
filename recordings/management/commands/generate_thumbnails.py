import hashlib
import os
import subprocess
import tempfile
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from recordings.models import RecordingItem

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
        items = RecordingItem.objects.exclude(
            old_video_url=""
        ).order_by("id")
        if options["missing"]:
            items = items.filter(
                thumbnail_path=""
            )
        if options["limit"]:
            items = items[:options["limit"]]
        thumbnail_dir = os.path.join(
            settings.MEDIA_ROOT,
            "thumbnails",
        )
        os.makedirs(
            thumbnail_dir,
            exist_ok=True,
        )
        processed = 0
        for item in items:
            self.stdout.write(
                f"Verwerken: {item.signbank_id} - {item.gloss_id}"
            )
            temp_path = None
            try:
                sha256 = hashlib.sha256()
                with tempfile.NamedTemporaryFile(
                    suffix=".mp4",
                    delete=False,
                ) as temp_file:
                    temp_path = temp_file.name
                    response = requests.get(
                        item.old_video_url,
                        stream=True,
                        timeout=120,
                    )
                    response.raise_for_status()
                    for chunk in response.iter_content(
                        chunk_size=1024 * 1024
                    ):
                        if not chunk:
                            continue
                        sha256.update(chunk)
                        temp_file.write(chunk)
                new_hash = sha256.hexdigest()
                # Video is niet gewijzigd en thumbnail bestaat nog
                if (
                    item.video_hash == new_hash
                    and item.thumbnail_path
                ):
                    full_thumbnail_path = os.path.join(
                        settings.MEDIA_ROOT,
                        item.thumbnail_path,
                    )
                    if os.path.exists(full_thumbnail_path):
                        self.stdout.write(
                            self.style.WARNING(
                                "  Ongewijzigd - overslaan"
                            )
                        )
                        continue
                thumbnail_filename = (
                    f"{item.signbank_id}.jpg"
                )
                thumbnail_relative_path = os.path.join(
                    "thumbnails",
                    thumbnail_filename,
                )
                thumbnail_full_path = os.path.join(
                    settings.MEDIA_ROOT,
                    thumbnail_relative_path,
                )
                # Duur van video uitlezen
                duration_result = subprocess.run(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        temp_path,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                duration = float(
                    duration_result.stdout.strip()
                )
                middle = duration / 2
                # Frame uit midden van video maken
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-ss",
                        str(middle),
                        "-i",
                        temp_path,
                        "-frames:v",
                        "1",
                        "-vf",
                        "scale=240:-2",
                        "-q:v",
                        "3",
                        thumbnail_full_path,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                item.video_hash = new_hash
                item.thumbnail_path = (
                    thumbnail_relative_path
                )
                item.save(
                    update_fields=[
                        "video_hash",
                        "thumbnail_path",
                    ]
                )
                processed += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        "  Thumbnail gemaakt"
                    )
                )
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(
                        f"  FOUT: {exc}"
                    )
                )
            finally:
                if (
                    temp_path
                    and os.path.exists(temp_path)
                ):
                    os.remove(temp_path)
        self.stdout.write(
            self.style.SUCCESS(
                f"Klaar. {processed} thumbnails gemaakt."
            )
        )