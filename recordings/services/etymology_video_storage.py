import hashlib
import os
import shutil
import tempfile

from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import uuid4

from django.conf import settings
from .signbank_service import SignbankService
from .signbank_video_archive import (
    _checked_copy,
    _sync_directory,
)

def _target_path(signbank_id, gloss, pair_number):
    if type(signbank_id) is not int or signbank_id <= 0:
        raise ValueError("Ongeldig Signbank-ID.")

    if type(pair_number) is not int or pair_number < 0:
        raise ValueError("Ongeldig etymologiepaarnummer.")

    gloss = gloss.strip()

    if (
        not gloss
        or gloss in {".", ".."}
        or any(character in gloss for character in ("/", "\\", "\x00"))
    ):
        raise ValueError("Ongeldige GLOSS.")

    root = Path(settings.SIGNBANK_ETYMOLOGYVIDEO_ROOT).resolve()

    folder = gloss[:2].upper()
    filename = f"{gloss}-{pair_number}-{signbank_id}.mp4"
    target = (root / folder / filename).resolve()

    if not target.is_relative_to(root):
        raise ValueError("Ongeldig videopad.")

    return root, target


def _video_url(root, target):
    relative = target.relative_to(root).as_posix()

    return (
        settings.SIGNBANK_ETYMOLOGYVIDEO_BASE_URL.rstrip("/")
        + "/"
        + quote(relative, safe="/")
    )


def _sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()

def archive_etymology_video(video_url):
    original_url = (video_url or "").strip()

    if not original_url:
        return None

    base = urlsplit(
        settings.SIGNBANK_ETYMOLOGYVIDEO_BASE_URL.rstrip("/") + "/"
    )
    parsed = urlsplit(original_url)

    # Alleen bestanden uit onze eigen etymologievideomap.
    # Een Vimeo-link heeft hier geen lokaal videobestand.
    if (
        parsed.scheme != base.scheme
        or parsed.netloc != base.netloc
        or not parsed.path.startswith(base.path)
    ):
        return None

    video_root = Path(
        settings.SIGNBANK_ETYMOLOGYVIDEO_ROOT
    ).resolve()

    archive_root = Path(
        settings.SIGNBANK_ETYMOLOGY_ARCHIVE_ROOT
    ).resolve()

    if (
        archive_root.is_relative_to(video_root)
        or video_root.is_relative_to(archive_root)
    ):
        raise ValueError(
            "Het etymologiearchief moet buiten de videomap staan."
        )

    relative_url = parsed.path[len(base.path):]
    candidate = video_root / unquote(relative_url)

    if candidate.is_symlink():
        raise ValueError(
            "Een symbolische koppeling kan niet worden gearchiveerd."
        )

    source = candidate.resolve()

    if (
        not source.is_relative_to(video_root)
        or source.suffix.lower() != ".mp4"
    ):
        raise ValueError("Ongeldig etymologievideopad.")

    if not source.is_file() or source.stat().st_size == 0:
        raise ValueError(
            "De oude etymologievideo ontbreekt of is leeg. "
            "Vervangen is gestopt."
        )

    relative = source.relative_to(video_root)
    archive_directory = archive_root / relative.parent
    archive_directory.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(
        ZoneInfo("Europe/Brussels")
    ).strftime("%y-%m-%d-%H-%M-%S")

    archived = archive_directory / (
        f"{source.stem}-{stamp}-{uuid4().hex}.mp4"
    )

    temporary = _checked_copy(source, archive_directory)

    try:
        checksum = _sha256(temporary)

        # Publiceer alleen een volledig gecontroleerde kopie.
        os.link(temporary, archived)
        _sync_directory(archive_directory)
    finally:
        temporary.unlink(missing_ok=True)

    return {
        "path": source,
        "url": _video_url(video_root, source),
        "archive_path": archived,
        "sha256": checksum,
    }

def store_etymology_video(
    prepared_video_path,
    signbank_id,
    gloss,
    pair_number,
):
    source = Path(prepared_video_path).resolve()

    if (
        not source.is_file()
        or source.suffix.lower() != ".mp4"
        or source.stat().st_size == 0
    ):
        raise ValueError("Er is geen verwerkte MP4-video beschikbaar.")

    root, target = _target_path(
        signbank_id,
        gloss,
        pair_number,
    )

    target.parent.mkdir(parents=True, exist_ok=True)

    temporary = None
    published = False

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".etymology-",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as destination:
            temporary = Path(destination.name)

            with source.open("rb") as video:
                shutil.copyfileobj(video, destination)

            destination.flush()
            os.fchmod(destination.fileno(), 0o644)
            os.fsync(destination.fileno())

        if _sha256(source) != _sha256(temporary):
            raise OSError("De videokopie wijkt af van het origineel.")

        # Bestaande video's worden hier niet overschreven.
        # Vervangen met archivering sluiten we apart aan.
        os.link(temporary, target)
        published = True

        return {
            "signbank_id": signbank_id,
            "gloss": gloss.strip(),
            "pair_number": pair_number,
            "path": target,
            "url": _video_url(root, target),
        }

    except FileExistsError as exc:
        raise ValueError(
            "Voor dit etymologiepaar bestaat al een videobestand."
        ) from exc

    except Exception:
        if published:
            target.unlink(missing_ok=True)
        raise

    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def discard_unused_etymology_video(stored):
    root, expected_path = _target_path(
        stored["signbank_id"],
        stored["gloss"],
        stored["pair_number"],
    )

    path = Path(stored["path"]).resolve()
    expected_url = _video_url(root, expected_path)

    if path != expected_path or stored["url"] != expected_url:
        raise ValueError("Videopad en videolink komen niet overeen.")

    service = SignbankService()

    with service.write_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")

        referenced = conn.execute(
            """
            SELECT 1
            FROM dictionary_definition
            WHERE LOWER(role) = 'ety'
              AND (
                  TRIM(text) = ?
                  OR instr(TRIM(text), ?) = 1
                  OR instr(TRIM(text), ?) = 1
              )
            LIMIT 1
            """,
            (
                expected_url,
                expected_url + "?",
                expected_url + "#",
            ),
        ).fetchone()

        if referenced:
            return False

        path.unlink(missing_ok=True)

    return True