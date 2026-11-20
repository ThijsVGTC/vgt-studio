from zoneinfo import ZoneInfo

from django.core.validators import URLValidator
from django.utils import timezone

from .signbank_service import SignbankService


NOTE_ROLES = {
    "video": "ety",
    "tekst": "etymology_text",
}


def get_role(note_type):
    if note_type not in NOTE_ROLES:
        raise ValueError("Ongeldig etymologietype.")

    return NOTE_ROLES[note_type]


def check_gloss_and_user(conn, signbank_id, signbank_user_id):
    gloss = conn.execute(
        "SELECT id FROM dictionary_gloss WHERE id = ?",
        (signbank_id,),
    ).fetchone()

    if gloss is None:
        raise ValueError("Gebaar niet gevonden in Signbank.")

    user = conn.execute(
        "SELECT id FROM auth_user WHERE id = ? AND is_active = 1",
        (signbank_user_id,),
    ).fetchone()

    if user is None:
        raise ValueError("Geen actieve Signbank-gebruiker gevonden.")


def update_last_author(conn, signbank_id, signbank_user_id):
    updated_at = timezone.localtime(
        timezone.now(),
        timezone=ZoneInfo("Europe/Brussels"),
    ).strftime("%Y-%m-%d %H:%M:%S.%f")

    conn.execute(
        "UPDATE dictionary_gloss SET lastUpdated = ? WHERE id = ?",
        (updated_at, signbank_id),
    )

    conn.execute(
        "DELETE FROM dictionary_gloss_lastUpdater WHERE gloss_id = ?",
        (signbank_id,),
    )

    conn.execute(
        """
        INSERT INTO dictionary_gloss_lastUpdater (gloss_id, user_id)
        VALUES (?, ?)
        """,
        (signbank_id, signbank_user_id),
    )


def save_etymology_note(
    signbank_id,
    note_type,
    text,
    signbank_user_id,
    note_id=None,
):
    role = get_role(note_type)
    text = text.strip()

    if not text:
        raise ValueError("Vul eerst een waarde in.")

    if note_type == "video":
        URLValidator(schemes=["http", "https"])(text)

    service = SignbankService()

    with service.write_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")

        check_gloss_and_user(
            conn,
            signbank_id,
            signbank_user_id,
        )

        if note_id is None:
            position = conn.execute(
                """
                SELECT COALESCE(MAX(count), -1) + 1 AS next_count
                FROM dictionary_definition
                WHERE gloss_id = ? AND LOWER(role) = ?
                """,
                (signbank_id, role),
            ).fetchone()["next_count"]

            cursor = conn.execute(
                """
                INSERT INTO dictionary_definition
                    (gloss_id, role, text, count, published)
                VALUES (?, ?, ?, ?, ?)
                """,
                (signbank_id, role, text, position, 0),
            )

            note_id = cursor.lastrowid

        else:
            note = conn.execute(
                """
                SELECT id
                FROM dictionary_definition
                WHERE id = ? AND gloss_id = ? AND LOWER(role) = ?
                """,
                (note_id, signbank_id, role),
            ).fetchone()

            if note is None:
                raise ValueError(
                    "Deze etymologienotitie hoort niet bij dit gebaar "
                    "of heeft een ander type."
                )

            conn.execute(
                """
                UPDATE dictionary_definition
                SET text = ?
                WHERE id = ? AND gloss_id = ? AND LOWER(role) = ?
                """,
                (text, note_id, signbank_id, role),
            )

        update_last_author(
            conn,
            signbank_id,
            signbank_user_id,
        )

    return note_id


def delete_etymology_note(
    signbank_id,
    note_type,
    note_id,
    signbank_user_id,
):
    role = get_role(note_type)
    service = SignbankService()

    with service.write_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")

        check_gloss_and_user(
            conn,
            signbank_id,
            signbank_user_id,
        )

        cursor = conn.execute(
            """
            DELETE FROM dictionary_definition
            WHERE id = ? AND gloss_id = ? AND LOWER(role) = ?
            """,
            (note_id, signbank_id, role),
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Deze etymologienotitie hoort niet bij dit gebaar "
                "of bestaat niet meer."
            )

        update_last_author(
            conn,
            signbank_id,
            signbank_user_id,
        )