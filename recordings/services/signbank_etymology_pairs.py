import hashlib
import json

from django.core.validators import URLValidator

from .signbank_service import SignbankService
from .signbank_etymology import (
    check_gloss_and_user,
    update_last_author,
)


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
):
    video_url = video_url.strip()
    text = text.strip()

    if not video_url:
        raise ValueError("Voeg een video of Vimeo-link toe.")

    if not text:
        raise ValueError("Vul de bijbehorende etymologietekst in.")

    URLValidator(schemes=["http", "https"])(video_url)

    if pair_number is not None and (
        type(pair_number) is not int
        or pair_number < 0
    ):
        raise ValueError("Ongeldig paarnummer.")

    service = SignbankService()

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
                    "De bestaande notities moeten eerst gekoppeld worden."
                )

            if expected_revision != pair["revision"]:
                raise ValueError(
                    "Dit etymologiepaar is ondertussen gewijzigd. "
                    "Laad de gegevens opnieuw voordat je opslaat."
                )

        existing_by_role = {
            row["role"]: row
            for row in existing
        }

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
                        0,
                    ),
                )

            else:
                conn.execute(
                    """
                    UPDATE dictionary_definition
                    SET text = ?
                    WHERE id = ?
                      AND gloss_id = ?
                      AND LOWER(role) = ?
                      AND count = ?
                    """,
                    (
                        value,
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