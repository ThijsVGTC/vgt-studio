import logging
import shutil
import subprocess
import tempfile

from contextlib import contextmanager
from pathlib import Path


logger = logging.getLogger(__name__)


class VideoProcessingError(ValueError):
    pass


@contextmanager
def prepare_signbank_video(uploaded_video):
    """
    Zet een upload of webcamopname om naar MP4.

    Het tijdelijke resultaat blijft beschikbaar zolang de
    aanroepende code binnen het with-blok werkt.
    """
    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg is None:
        raise VideoProcessingError(
            "De videoverwerking is niet beschikbaar op de server."
        )

    with tempfile.TemporaryDirectory(prefix="studio-video-") as directory:
        directory = Path(directory)

        source_path = directory / "original.upload"
        output_path = directory / "converted.mp4"

        uploaded_video.seek(0)

        total_bytes = 0

        with source_path.open("wb") as destination:
            for chunk in uploaded_video.chunks():
                destination.write(chunk)
                total_bytes += len(chunk)

        if total_bytes == 0:
            raise VideoProcessingError(
                "De video is leeg. Upload een andere video "
                "of maak een nieuwe opname."
            )

        command = [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-xerror",
            "-y",

            "-protocol_whitelist", "file,pipe",
            "-format_whitelist",
            "mov,mp4,m4a,3gp,3g2,mj2,matroska,webm,avi,mpeg,mpegts,ogg",

            "-i", str(source_path),

            "-map", "0:V:0",
            "-an",
            "-sn",
            "-dn",
            "-map_metadata", "-1",
            "-map_chapters", "-1",

            "-vf", "scale=w='trunc(min(1280,iw)/2)*2':h=-2",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-maxrate", "800k",
            "-bufsize", "1600k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",

            str(output_path),
        ]

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise VideoProcessingError(
                "Het verwerken van de video duurt te lang. "
                "Probeer een kortere video."
            ) from exc
        except OSError as exc:
            logger.exception("Videoverwerking kon niet starten")

            raise VideoProcessingError(
                "De videoverwerking kon niet worden gestart."
            ) from exc

        if result.returncode != 0:
            logger.warning(
                "Video omzetten mislukt: %s",
                result.stderr[-4000:],
            )

            raise VideoProcessingError(
                "De video kon niet worden verwerkt. "
                "Upload een andere video of maak een nieuwe opname."
            )

        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise VideoProcessingError(
                "Er is geen bruikbare video aangemaakt."
            )

        yield output_path