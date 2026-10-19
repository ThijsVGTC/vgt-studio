import os
import sqlite3
from contextlib import contextmanager


class SignbankService:
    """
    Centrale verbinding met Signbank 2.0.

    Huidige backend: SQLite
    Toekomstige backend: Signbank API

    Onafhankelijk van de database van VGT Studio.
    """

    def __init__(self):
        self.db_path = os.environ.get(
            "SIGNBANK_DB_PATH",
            "/app/signbank/signbank.db",
        )

    @contextmanager
    def connection(self):
        """
        Open een read-only verbinding met de Signbank-master.
        Sluit de verbinding altijd na gebruik.
        """

        uri = f"file:{self.db_path}?mode=ro"

        conn = sqlite3.connect(
            uri,
            uri=True,
            timeout=5,
        )

        conn.row_factory = sqlite3.Row

        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def write_connection(self):
        """
        Open een schrijfverbinding met de Signbank-master.

        Wijzigingen worden alleen opgeslagen als de volledige
        transactie succesvol is.
        """

        uri = f"file:{self.db_path}?mode=rw"

        conn = sqlite3.connect(
            uri,
            uri=True,
            timeout=5,
        )

        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_gloss(self, signbank_id):
        """
        Haal de bewerkbare basisgegevens van één gebaar
        rechtstreeks uit de Signbank-master.
        """

        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    annotation_idgloss,
                    subhndsh,
                    final_subhndsh,
                    locprim,
                    final_loc,
                    semField,
                    semField1,
                    semField2,
                    semField3,
                    semField4,
                    inWeb,
                    lastUpdated
                FROM dictionary_gloss
                WHERE id = ?
                """,
                (signbank_id,),
            ).fetchone()

            if row is None:
                return None

            return dict(row)

    def update_gloss(self, signbank_id, old_gloss, new_gloss):
        """
        Wijzig de GLOSS-naam in de Signbank-master.

        Controleer eerst of de oorspronkelijke waarde
        nog overeenkomt met de masterdatabase.
        """

        new_gloss = new_gloss.strip()

        if not new_gloss:
            raise ValueError("GLOSS mag niet leeg zijn.")

        with self.write_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE dictionary_gloss
                SET annotation_idgloss = ?
                WHERE id = ?
                AND annotation_idgloss = ?
                """,
                (new_gloss, signbank_id, old_gloss),
            )

            if cursor.rowcount == 0:
                raise ValueError(
                    "Het gebaar is ondertussen gewijzigd of bestaat niet meer. "
                    "Vernieuw de gegevens voordat je opnieuw opslaat."
                )

        return self.get_gloss(signbank_id)