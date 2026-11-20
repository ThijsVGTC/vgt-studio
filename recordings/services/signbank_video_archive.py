import fcntl
import hashlib
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings


def _sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _checked_copy(source, directory):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=directory, prefix=".video-", suffix=".tmp", delete=False
        ) as output:
            temporary = Path(output.name)
            with source.open("rb") as input_file:
                shutil.copyfileobj(input_file, output)
            output.flush()
            os.fsync(output.fileno())

        if _sha256(source) != _sha256(temporary):
            raise OSError("De videokopie wijkt af van het origineel.")
        return temporary
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def replace_signbank_video(source_path, target_path):
    source = Path(source_path).resolve()
    target = Path(target_path).resolve()
    video_root = Path(settings.SIGNBANK_GLOSSVIDEO_ROOT).resolve()
    archive_root = Path(settings.SIGNBANK_ARCHIVE_ROOT).resolve()
    relative = target.relative_to(video_root)

    if archive_root.is_relative_to(video_root) or video_root.is_relative_to(archive_root):
        raise ValueError("Het videoarchief moet buiten de Signbank-videomap staan.")
    if source == target:
        raise ValueError("Bronvideo en doelvideo mogen niet hetzelfde bestand zijn.")

    target.parent.mkdir(parents=True, exist_ok=True)
    lock_directory = archive_root / ".locks"
    lock_directory.mkdir(parents=True, exist_ok=True)
    lock_name = hashlib.sha256(str(relative).encode()).hexdigest() + ".lock"

    with (lock_directory / lock_name).open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        new_copy = None
        old_copy = None
        try:
            new_copy = _checked_copy(source, target.parent)
            mode = (target.stat().st_mode & 0o777) if target.exists() else 0o644
            new_copy.chmod(mode)
            archived = None

            if target.exists():
                archive_directory = archive_root / relative.parent
                archive_directory.mkdir(parents=True, exist_ok=True)
                old_copy = _checked_copy(target, archive_directory)
                stamp = datetime.now(ZoneInfo("Europe/Brussels")).strftime("%y-%m-%d-%H-%M")
                number = 0

                while True:
                    extra = f"-{number}" if number else ""
                    archived = archive_directory / (
                        f"{target.stem}-{stamp}{extra}{target.suffix}"
                    )
                    try:
                        os.link(old_copy, archived)
                        break
                    except FileExistsError:
                        number += 1

                old_copy.unlink()
                old_copy = None
                _sync_directory(archive_directory)

            os.replace(new_copy, target)
            new_copy = None
            _sync_directory(target.parent)
            return archived
        finally:
            if new_copy is not None:
                new_copy.unlink(missing_ok=True)
            if old_copy is not None:
                old_copy.unlink(missing_ok=True)
