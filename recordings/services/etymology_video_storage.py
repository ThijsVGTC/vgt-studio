import hashlib
import os
import shutil
import tempfile

from pathlib import Path
from urllib.parse import quote

from django.conf import settings

from .signbank_service import SignbankService


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