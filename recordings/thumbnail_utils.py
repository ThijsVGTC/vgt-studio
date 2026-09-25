import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

import requests
from django.conf import settings


def generate_thumbnail_for_item(
    item,
    source_path=None,
    force=False,
):
    """
    Genereer of vernieuw de thumbnail van één RecordingItem.

    source_path:
        Optioneel lokaal videobestand.
        Indien leeg wordt item.old_video_url gedownload.

    force:
        True = thumbnail altijd opnieuw genereren.

    Geeft terug:
        (True, "melding") bij succes
        (False, "foutmelding") bij fout
    """

    temp_path = None

    try:

        # --------------------------------------------
        # Videobron bepalen + hash berekenen
        # --------------------------------------------

        if source_path:

            video_path = Path(source_path)

            if not video_path.exists():
                return (
                    False,
                    f"Videobestand bestaat niet: {video_path}",
                )

            sha256 = hashlib.sha256()

            with video_path.open("rb") as video_file:

                for chunk in iter(
                    lambda: video_file.read(1024 * 1024),
                    b"",
                ):
                    sha256.update(chunk)

            new_hash = sha256.hexdigest()

        else:

            if not item.old_video_url:
                return (
                    False,
                    "Geen oude video-URL beschikbaar.",
                )

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

            video_path = Path(temp_path)
            new_hash = sha256.hexdigest()

        # --------------------------------------------
        # Thumbnailpad
        # --------------------------------------------

        thumbnail_dir = (
            Path(settings.MEDIA_ROOT)
            / "thumbnails"
        )

        thumbnail_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        thumbnail_relative_path = (
            Path("thumbnails")
            / f"{item.signbank_id}.jpg"
        )

        thumbnail_full_path = (
            Path(settings.MEDIA_ROOT)
            / thumbnail_relative_path
        )

        # --------------------------------------------
        # Overslaan indien alles al actueel is
        # --------------------------------------------

        if (
            not force
            and item.video_hash == new_hash
            and item.thumbnail_path
            and thumbnail_full_path.exists()
        ):
            return (
                True,
                "Thumbnail is al actueel.",
            )

        # --------------------------------------------
        # Videoduur bepalen
        # --------------------------------------------

        duration_result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        duration = float(
            duration_result.stdout.strip()
        )

        middle = duration / 2

        # --------------------------------------------
        # Thumbnail maken
        # --------------------------------------------

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(middle),
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-vf",
                "scale=240:-2",
                "-q:v",
                "3",
                str(thumbnail_full_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        # --------------------------------------------
        # Database bijwerken
        # --------------------------------------------

        item.video_hash = new_hash

        item.thumbnail_path = str(
            thumbnail_relative_path
        )

        item.save(
            update_fields=[
                "video_hash",
                "thumbnail_path",
            ]
        )

        return (
            True,
            "Thumbnail gemaakt.",
        )

    except Exception as exc:

        return (
            False,
            str(exc),
        )

    finally:

        if (
            temp_path
            and os.path.exists(temp_path)
        ):
            os.remove(temp_path)