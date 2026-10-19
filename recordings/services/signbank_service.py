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

        self.video_root = os.environ.get(
            "SIGNBANK_VIDEO_ROOT",
            "/app/signbank/writable/glossvideo",
        )

    def get_video_path(self, gloss, signbank_id):
        """
        Bepaal het videopad volgens de mapstructuur van Signbank 2.0.

        Voorbeeld:
        BEELD-B, 1063
        -> glossvideo/BE/BEELD-B-1063.mp4
        """

        from pathlib import Path

        if not gloss or gloss in {".", ".."}:
            raise ValueError("Ongeldige GLOSS.")

        if "/" in gloss or "\\" in gloss:
            raise ValueError("GLOSS mag geen schuine strepen bevatten.")

        return (
            Path(self.video_root)
            / gloss[:2]
            / f"{gloss}-{int(signbank_id)}.mp4"
        )

    def move_gloss_video(self, signbank_id, old_gloss, new_gloss):
        """
        Verplaats de video wanneer de GLOSS verandert.
        Overschrijf nooit een bestaande video.
        """

        import os

        old_path = self.get_video_path(old_gloss, signbank_id)
        new_path = self.get_video_path(new_gloss, signbank_id)

        if old_path == new_path:
            return False

        if not old_path.is_file():
            return False

        if new_path.exists():
            raise FileExistsError(
                f"Er bestaat al een video op de bestemming: {new_path}"
            )

        new_path.parent.mkdir(parents=True, exist_ok=True)

        os.link(old_path, new_path)

        try:
            os.unlink(old_path)
        except OSError:
            try:
                os.unlink(new_path)
            except OSError as cleanup_error:
                raise RuntimeError(
                    "De video kon niet volledig worden verplaatst. "
                    "Beide videopaden moeten handmatig gecontroleerd worden."
                ) from cleanup_error

            raise

        return True

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
        Wijzig een GLOSS in de Signbank-master en verplaats
        de bijbehorende video.

        Bij een fout wordt de database teruggedraaid en
        proberen we de video naar de oude locatie terug te zetten.
        """

        new_gloss = new_gloss.strip()

        if not new_gloss:
            raise ValueError("GLOSS mag niet leeg zijn.")

        # Controleer de bestandsnamen voordat we iets wijzigen.
        old_video = self.get_video_path(old_gloss, signbank_id)
        new_video = self.get_video_path(new_gloss, signbank_id)

        if old_gloss == new_gloss:
            return self.get_gloss(signbank_id)

        video_moved = False

        try:
            with self.write_connection() as conn:
                # Voorkom gelijktijdige schrijfacties tijdens de wijziging.
                conn.execute("BEGIN IMMEDIATE")

                row = conn.execute(
                    """
                    SELECT annotation_idgloss
                    FROM dictionary_gloss
                    WHERE id = ?
                    """,
                    (signbank_id,),
                ).fetchone()

                if row is None or row["annotation_idgloss"] != old_gloss:
                    raise ValueError(
                        "Dit gebaar is ondertussen gewijzigd. "
                        "Vernieuw de gegevens."
                    )

                existing = conn.execute(
                    """
                    SELECT id
                    FROM dictionary_gloss
                    WHERE annotation_idgloss = ?
                        AND id != ?
                    """,
                    (new_gloss, signbank_id),
                ).fetchone()

                if existing:
                    raise ValueError(
                        f"De GLOSS '{new_gloss}' bestaat al in Signbank."
                )

                existing = conn.execute(
                    """
                    SELECT id
                    FROM dictionary_gloss
                    WHERE annotation_idgloss = ?
                    AND id != ?
                    """,
                    (new_gloss, signbank_id),
                ).fetchone()

                if existing:
                    raise ValueError(
                        f"De GLOSS '{new_gloss}' bestaat al in Signbank."
                    )

                # Verplaats de video voordat de database wordt opgeslagen.
                video_moved = self.move_gloss_video(
                    signbank_id,
                    old_gloss,
                    new_gloss,
                )

                conn.execute(
                    """
                    UPDATE dictionary_gloss
                    SET annotation_idgloss = ?
                    WHERE id = ?
                    """,
                    (new_gloss, signbank_id),
                )

        except Exception:
            if video_moved:
                current_gloss = self.get_gloss(signbank_id)

                if current_gloss["annotation_idgloss"] != old_gloss:
                    raise RuntimeError(
                        "De database bevat mogelijk al de nieuwe GLOSS, "
                        "maar de bewerking is niet volledig afgerond. "
                        "Controleer de database en video handmatig."
                    )
                try:
                    if old_video.exists():
                        raise FileExistsError(
                            "Het oorspronkelijke videopad bestaat al."
                        )

                    os.link(new_video, old_video)
                    os.unlink(new_video)

                except Exception as rollback_error:
                    raise RuntimeError(
                        "De GLOSS-wijziging is mislukt en de video "
                        "kon niet automatisch worden teruggezet. "
                        "Handmatige controle is noodzakelijk."
                    ) from rollback_error

            raise

        return self.get_gloss(signbank_id)