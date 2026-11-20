#!/usr/bin/env python3
"""Upload complete Signbank archives. Preview by default; --apply removes verified copies."""

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def signature(path):
    value = path.stat()
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def local_md5(path):
    digest = hashlib.md5()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_rclone(binary, *arguments):
    result = subprocess.run(
        [str(binary), *arguments],
        capture_output=True,
        text=True,
        timeout=3600,
        check=False,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Rclone mislukt.")[-2000:].strip())
    return result.stdout


def audit(log_path, event, **details):
    record = {
        "time": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **details,
    }
    with log_path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(record, ensure_ascii=False) + "\n")
        output.flush()
        os.fsync(output.fileno())


def upload_one(path, root, remote_root, binary, log_path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Geen gewoon archiefbestand.")
    relative = path.relative_to(root).as_posix()
    path.resolve().relative_to(root)
    remote = remote_root.rstrip("/") + "/" + relative
    initial = signature(path)
    checksum = local_md5(path)
    if signature(path) != initial:
        raise RuntimeError("Archiefbestand is tijdens de controle veranderd.")

    # Een bestaande afwijkende Drive-back-up mag nooit worden overschreven.
    run_rclone(
        binary, "copyto", str(path), remote,
        "--checksum", "--immutable", "--retries", "3",
        "--low-level-retries", "5", "--contimeout", "30s", "--timeout", "5m",
    )
    metadata = json.loads(run_rclone(binary, "lsjson", remote, "--stat", "--hash"))
    if not isinstance(metadata, dict) or metadata.get("IsDir") is not False:
        raise RuntimeError("Drive bevestigt geen gewoon videobestand.")
    hashes = {key.lower(): value for key, value in (metadata.get("Hashes") or {}).items()}
    if metadata.get("Size") != initial[2] or hashes.get("md5", "").lower() != checksum:
        raise RuntimeError("Grootte of inhoud op Drive komt niet overeen; lokale kopie blijft bewaard.")
    if not metadata.get("ID"):
        raise RuntimeError("Drive-bestands-ID ontbreekt; lokale kopie blijft bewaard.")
    if signature(path) != initial or local_md5(path) != checksum or signature(path) != initial:
        raise RuntimeError("Lokale kopie is gewijzigd; bestand wordt niet verwijderd.")

    # Eerst een duurzaam bewijs opslaan, pas daarna de lokale kopie verwijderen.
    audit(
        log_path, "upload_verified", file=relative, remote=remote,
        drive_id=metadata["ID"], size=initial[2], md5=checksum,
    )
    path.unlink()
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    audit(log_path, "local_copy_removed", file=relative, drive_id=metadata["ID"])
    return remote


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Upload, controleer en verwijder lokale kopieën.")
    parser.add_argument("--root", type=Path, default=Path("/var/www/vhosts/vlaamsegebarentaal.be/mov/glossvideo"))
    parser.add_argument("--remote", default="vgtc:signbank/glossvideo")
    parser.add_argument("--rclone", type=Path, default=Path.home() / ".local/bin/rclone")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        parser.error("De archiefmap bestaat niet: " + str(root))
    if args.apply and (not args.rclone.is_file() or not os.access(args.rclone, os.X_OK)):
        parser.error("Rclone is niet uitvoerbaar: " + str(args.rclone))
    if ":" not in args.remote:
        parser.error("Gebruik een rclone-doel, bijvoorbeeld vgtc:signbank/glossvideo.")

    log_path = root.parent / "signbank-drive-backup.jsonl"
    with (root / ".upload.lock").open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Een vorige uploadtaak draait nog; deze poging stopt.", flush=True)
            return 0

        count = 0
        failures = 0
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if any(part.startswith(".") for part in relative.parts):
                continue
            if path.suffix.lower() != ".mp4" or not path.is_file():
                continue
            try:
                if path.is_symlink():
                    raise ValueError("Symbolische koppelingen worden niet verwerkt.")
                path.resolve().relative_to(root)
                if not args.apply:
                    print("VOORBEELD: " + str(relative) + " -> " + args.remote.rstrip("/") + "/" + relative.as_posix(), flush=True)
                else:
                    remote = upload_one(path, root, args.remote, args.rclone, log_path)
                    print("GECONTROLEERD EN LOKAAL VERWIJDERD: " + remote, flush=True)
                count += 1
            except Exception as error:
                failures += 1
                print("FOUT: " + str(relative) + ": " + str(error), flush=True)
                if args.apply:
                    audit(log_path, "error", file=relative.as_posix(), message=str(error))

        label = "Verwerkt" if args.apply else "Gevonden (niets geüpload of verwijderd)"
        print(f"{label}: {count}; fouten: {failures}", flush=True)
        return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
