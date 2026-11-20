import hashlib
import json

from django.core.validators import URLValidator

from .signbank_service import SignbankService
from .signbank_etymology import (
    check_gloss_and_user,
    update_last_author,
)

import logging

from .etymology_video_storage import (
    store_etymology_video,
    discard_unused_etymology_video,
)

logger = logging.getLogger(__name__)

def _read_notes(conn, signbank_id, pair_number=None):
    query = """
        SELECT
            id,
            LOWER(role) AS role,
            text,
            count,
            published
        FROM dictionary_definition
        WHERE gloss_id = ?
          AND LOWER(role) IN ('ety', 'etymology_text')
    """

    parameters = [signbank_id]

    if pair_number is not None:
        query += " AND count = ?"
        parameters.append(pair_number)

    query += " ORDER BY count ASC, id ASC"

    return conn.execute(query, parameters).fetchall()


def _revision(rows):
    content = json.dumps(
        [dict(row) for row in rows],
        sort_keys=True,
        ensure_ascii=False,
    )

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def _pair_data(pair_number, rows):
    videos = [
        {
            "id": row["id"],
            "text": row["text"] or "",
        }
        for row in rows
        if row["role"] == "ety"
    ]

    texts = [
        {
            "id": row["id"],
            "text": row["text"] or "",
        }
        for row in rows
        if row["role"] == "etymology_text"
    ]

    

    return {
        "pairNumber": pair_number,
        "videos": videos,
        "texts": texts,
        "published": bool(rows) and all(bool(row["published"]) for row in rows),
        "revision": _revision(rows),
        "ambiguous": (
            type(pair_number) is not int
            or pair_number < 0
            or len(videos) > 1
            or len(texts) > 1
        ),
        
    }


def get_etymology_pairs(signbank_id):
    service = SignbankService()

    with service.connection() as conn:
        rows = _read_notes(conn, signbank_id)

    groups = {}

    for row in rows:
        groups.setdefault(row["count"], []).append(row)

    return [
        _pair_data(pair_number, notes)
        for pair_number, notes in groups.items()
    ]

def save_etymology_pair(
    signbank_id,
    video_url,
    text,
    signbank_user_id,
    pair_number=None,
    expected_revision=None,
    prepared_video_path=None,
    keep_video=False,
    published=False,
):
    video_url = (video_url or "").strip()
    text = (text or "").strip()

    if pair_number is not None and (
        type(pair_number) is not int
        or pair_number < 0
    ):
        raise ValueError("Ongeldig paarnummer.")

    selected_sources = sum([
        bool(video_url),
        prepared_video_path is not None,
        bool(keep_video),
    ])

    if selected_sources != 1:
        raise ValueError("Kies precies één videobron.")

    if keep_video and pair_number is None:
        raise ValueError("Een nieuw paar heeft eerst een video nodig.")

    if video_url:
        URLValidator(schemes=["http", "https"])(video_url)

    service = SignbankService()
    stored = None

    try:
        with service.write_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")

            check_gloss_and_user(
                conn,
                signbank_id,
                signbank_user_id,
            )

            if pair_number is None:
                pair_number = conn.execute(
                    """
                    SELECT COALESCE(MAX(count), 0) + 1 AS next_number
                    FROM dictionary_definition
                    WHERE gloss_id = ?
                      AND LOWER(role) IN ('ety', 'etymology_text')
                    """,
                    (signbank_id,),
                ).fetchone()["next_number"]

                existing = []

            else:
                existing = _read_notes(
                    conn,
                    signbank_id,
                    pair_number,
                )

                if not existing:
                    raise ValueError(
                        "Dit etymologiepaar bestaat niet meer. "
                        "Laad de gegevens opnieuw."
                    )

                pair = _pair_data(pair_number, existing)

                if pair["ambiguous"]:
                    raise ValueError(
                        "Deze index bevat meerdere video's of teksten. "
                        "Koppel de bestaande notities eerst."
                    )

                if expected_revision != pair["revision"]:
                    raise ValueError(
                        "Dit paar is ondertussen gewijzigd. "
                        "Laad de gegevens opnieuw."
                    )

            existing_by_role = {
                row["role"]: row
                for row in existing
            }

            if keep_video:
                previous_video = existing_by_role.get("ety")

                if previous_video is None:
                    raise ValueError(
                        "Dit paar heeft nog geen video."
                    )

                video_url = (
                    previous_video["text"] or ""
                ).strip()

                if not video_url:
                    raise ValueError(
                        "Voeg eerst een video of Vimeo-link toe."
                    )

            elif prepared_video_path is not None:
                gloss_row = conn.execute(
                    """
                    SELECT annotation_idgloss
                    FROM dictionary_gloss
                    WHERE id = ?
                    """,
                    (signbank_id,),
                ).fetchone()

                stored = store_etymology_video(
                    prepared_video_path=prepared_video_path,
                    signbank_id=signbank_id,
                    gloss=gloss_row["annotation_idgloss"] or "",
                    pair_number=pair_number,
                )

                video_url = stored["url"]

            for role, value in (
                ("ety", video_url),
                ("etymology_text", text),
            ):
                previous = existing_by_role.get(role)

                if previous is None:
                    conn.execute(
                        """
                        INSERT INTO dictionary_definition
                            (gloss_id, role, text, count, published)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            signbank_id,
                            role,
                            value,
                            pair_number,
                            int(published),
                        ),
                    )

                else:
                    conn.execute(
                        """
                        UPDATE dictionary_definition
                        SET text = ?, published = ?
                        WHERE id = ?
                          AND gloss_id = ?
                          AND LOWER(role) = ?
                          AND count = ?
                        """,
                        (
                            value,
                            int(published),
                            previous["id"],
                            signbank_id,
                            role,
                            pair_number,
                        ),
                    )

            update_last_author(
                conn,
                signbank_id,
                signbank_user_id,
            )

            saved = _pair_data(
                pair_number,
                _read_notes(conn, signbank_id, pair_number),
            )

        return saved

    except Exception:
        if stored is not None:
            try:
                discard_unused_etymology_video(stored)
            except Exception:
                logger.exception(
                    "Upload behouden omdat de opslaguitkomst "
                    "niet gecontroleerd kon worden: %s",
                    stored["url"],
                )

        raise