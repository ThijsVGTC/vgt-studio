import os
import sqlite3
from contextlib import contextmanager
from zoneinfo import ZoneInfo
from django.utils import timezone

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

    def get_handshape_choices(self):
        """
        Haal alle beschikbare handvormen op uit de Signbank-master.
        """

        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT machine_value, dutch_name, english_name
                FROM dictionary_fieldchoice
                WHERE field = 'Handshape'
                ORDER BY CAST(machine_value AS INTEGER)
                """
            ).fetchall()

        return [
            {
                "code": str(row["machine_value"]),
                "name": row["dutch_name"] or row["english_name"] or "",
            }
            for row in rows
            if str(row["machine_value"]) != "0"
        ]

    def get_location_choices(self):
        """
        Haal alle beschikbare locaties op uit de Signbank-master.
        """

        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT machine_value, dutch_name, english_name
                FROM dictionary_fieldchoice
                WHERE field = 'Location'
                ORDER BY CAST(machine_value AS INTEGER)
                """
            ).fetchall()

        return [
            {
                "code": str(row["machine_value"]),
                "name": row["dutch_name"] or row["english_name"] or "",
            }
            for row in rows
            if str(row["machine_value"]) != "0"
        ]

    def get_translations(self, signbank_id):
        """
        Haal de afzonderlijke vertalingen van een gebaar op.
        """

        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    t.id,
                    t.translation_id,
                    t.language_id,
                    t."index",
                    k.text
                FROM dictionary_translation t
                INNER JOIN dictionary_keyword k
                    ON k.id = t.translation_id
                WHERE t.gloss_id = ?
                ORDER BY t."index", t.id
                """,
                (signbank_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    def add_translation(self, signbank_id, new_text, signbank_user_id):
        """
        Voeg een Nederlandse vertaling toe aan een bestaand gebaar.
        """

        new_text = new_text.strip()

        if not new_text or len(new_text) > 100:
            raise ValueError("Een vertaling moet 1 tot 100 tekens bevatten.")

        with self.write_connection() as conn:

            gloss = conn.execute(
                "SELECT id FROM dictionary_gloss WHERE id = ?",
                (signbank_id,),
            ).fetchone()

            if gloss is None:
                raise ValueError("Gebaar niet gevonden.")

            user = conn.execute(
                "SELECT id FROM auth_user WHERE id = ?",
                (signbank_user_id,),
            ).fetchone()

            if user is None:
                raise ValueError("Signbank-gebruiker niet gevonden.")

            # Zoek een bestaand keyword.
            keyword = conn.execute(
                "SELECT id FROM dictionary_keyword WHERE text = ?",
                (new_text,),
            ).fetchone()

            if keyword:
                keyword_id = keyword["id"]
            else:
                cursor = conn.execute(
                    "INSERT INTO dictionary_keyword (text) VALUES (?)",
                    (new_text,),
                )
                keyword_id = cursor.lastrowid

            # Voorkom dubbele vertalingen bij hetzelfde gebaar.
            existing = conn.execute(
                """
                SELECT id
                FROM dictionary_translation
                WHERE gloss_id = ?
                AND translation_id = ?
                AND language_id = 2
                """,
                (signbank_id, keyword_id),
            ).fetchone()

            if existing:
                raise ValueError("Deze vertaling bestaat al bij dit gebaar.")

            # Bepaal de volgende positie.
            next_index = conn.execute(
                """
                SELECT COALESCE(MAX("index"), -1) + 1
                FROM dictionary_translation
                WHERE gloss_id = ?
                """,
                (signbank_id,),
            ).fetchone()[0]

            conn.execute(
                """
                INSERT INTO dictionary_translation
                    (gloss_id, translation_id, language_id, "index")
                VALUES (?, ?, 2, ?)
                """,
                (signbank_id, keyword_id, next_index),
            )

            updated_at = timezone.localtime(
                timezone.now(),
                timezone=ZoneInfo("Europe/Brussels"),
            ).strftime("%Y-%m-%d %H:%M:%S.%f")

            conn.execute(
                """
                UPDATE dictionary_gloss
                SET lastUpdated = ?
                WHERE id = ?
                """,
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

        from django.core.management import call_command

        call_command(
            "sync_signbank",
            signbank_id=signbank_id,
            verbosity=0,
        )

    def update_translation(self, signbank_id, translation_row_id, new_text, signbank_user_id):
        """
        Wijzig één vertaling van een gebaar zonder gedeelde keywords
        van andere gebaren aan te passen.
        """

        new_text = new_text.strip()

        if not new_text or len(new_text) > 100:
            raise ValueError("Een vertaling moet 1 tot 100 tekens bevatten.")

        with self.write_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")

            row = conn.execute(
                """
                SELECT t.translation_id, k.text
                FROM dictionary_translation t
                JOIN dictionary_keyword k ON k.id = t.translation_id
                WHERE t.id = ? AND t.gloss_id = ?
                """,
                (translation_row_id, signbank_id),
            ).fetchone()

            if row is None:
                raise ValueError("Vertaling niet gevonden bij dit gebaar.")

            if row["text"] == new_text:
                return

            user = conn.execute(
                "SELECT 1 FROM auth_user WHERE id = ?",
                (signbank_user_id,),
            ).fetchone()

            if user is None:
                raise ValueError("Signbank-gebruiker niet gevonden.")

            keyword = conn.execute(
                "SELECT id FROM dictionary_keyword WHERE text = ?",
                (new_text,),
            ).fetchone()

            if keyword:
                keyword_id = keyword["id"]
            else:
                cursor = conn.execute(
                    "INSERT INTO dictionary_keyword (text) VALUES (?)",
                    (new_text,),
                )
                keyword_id = cursor.lastrowid

            conn.execute(
                """
                UPDATE dictionary_translation
                SET translation_id = ?
                WHERE id = ? AND gloss_id = ?
                """,
                (keyword_id, translation_row_id, signbank_id),
            )

            updated_at = timezone.localtime(
                timezone.now(),
                timezone=ZoneInfo("Europe/Brussels"),
            ).strftime("%Y-%m-%d %H:%M:%S.%f")

            conn.execute(
                """
                UPDATE dictionary_gloss
                SET lastUpdated = ?
                WHERE id = ?
                """,
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

        from django.core.management import call_command

        call_command(
            "sync_signbank",
            signbank_id=signbank_id,
            verbosity=0,
        )
    def update_gloss(self, signbank_id, old_gloss, new_gloss, signbank_user_id=None):
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

                # Verplaats de video voordat de database wordt opgeslagen.
                video_moved = self.move_gloss_video(
                    signbank_id,
                    old_gloss,
                    new_gloss,
                )

                conn.execute(
                    """
                    UPDATE dictionary_gloss
                    SET 
                        idgloss = ?,
                        annotation_idgloss = ?,
                        lastUpdated = ?
                    WHERE id = ?
                    """,
                    (new_gloss, new_gloss, timezone.localtime(timezone.now(),timezone=ZoneInfo("Europe/Brussels"),).strftime("%Y-%m-%d %H:%M:%S.%f"), signbank_id),
                )
                if signbank_user_id is not None:
                    # Controleer of de gebruiker in de Signbank-master bestaat.
                    user_exists = conn.execute(
                        "SELECT 1 FROM auth_user WHERE id = ?",
                        (signbank_user_id,),
                    ).fetchone()

                    if user_exists is None:
                        raise ValueError(
                            f"Signbank-gebruiker {signbank_user_id} bestaat niet."
                        )

                    # Registreer de gebruiker die deze GLOSS heeft gewijzigd.
                    conn.execute(
                        """
                        DELETE FROM dictionary_gloss_lastUpdater
                        WHERE gloss_id = ?
                        """,
                        (signbank_id,),
                    )

                    conn.execute(
                        """
                        INSERT INTO dictionary_gloss_lastUpdater
                            (gloss_id, user_id)
                        VALUES (?, ?)
                        """,
                        (signbank_id, signbank_user_id),
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

        # De wijziging in de Signbank-master is geslaagd.
        # Werk nu ook de lokale VGT Studio-database bij.
        from django.core.management import call_command
        from django.core.management.base import CommandError

        try:
            call_command(
                "sync_signbank",
                signbank_id=signbank_id,
                verbosity=0,
            )
        except Exception as exc:
            raise RuntimeError(
                f"De GLOSS is gewijzigd in Signbank, maar de synchronisatie "
                f"naar VGT Studio is mislukt voor Signbank ID {signbank_id}. "
                "De Signbank-master is niet teruggedraaid. "
                "Synchroniseer dit gebaar opnieuw."
            ) from exc

        return self.get_gloss(signbank_id)
    
    def update_in_woordenboek(self, signbank_id, in_woordenboek, signbank_user_id):
        """
        Wijzig 'In woordenboek' in de Signbank-master.
        Registreer de gebruiker en wijzigingsdatum.
        """

        if not isinstance(in_woordenboek, bool):
            raise ValueError("Ongeldige waarde voor 'In woordenboek'.")

        with self.write_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")

            row = conn.execute(
                "SELECT inWeb FROM dictionary_gloss WHERE id = ?",
                (signbank_id,),
            ).fetchone()

            if row is None:
                raise ValueError("Gebaar niet gevonden in Signbank.")

            if bool(row["inWeb"]) == in_woordenboek:
                return

            user = conn.execute(
                "SELECT id FROM auth_user WHERE id = ?",
                (signbank_user_id,),
            ).fetchone()

            if user is None:
                raise ValueError("Signbank-gebruiker niet gevonden.")

            updated_at = timezone.localtime(
                timezone.now(),
                timezone=ZoneInfo("Europe/Brussels"),
            ).strftime("%Y-%m-%d %H:%M:%S.%f")

            conn.execute(
                """
                UPDATE dictionary_gloss
                SET inWeb = ?, lastUpdated = ?
                WHERE id = ?
                """,
                (int(in_woordenboek), updated_at, signbank_id),
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

        from django.core.management import call_command

        call_command(
            "sync_signbank",
            signbank_id=signbank_id,
            verbosity=0,
        )
    def update_handvormen(
        self,
        signbank_id,
        handvorm_begin,
        handvorm_einde,
        signbank_user_id,
    ):
        """
        Wijzig de begin- en eindhandvorm in de Signbank-master.
        """

        def validate_code(value):
            value = str(value or "0").strip()

            if not value.isdigit():
                raise ValueError("Ongeldige handvormcode.")

            return int(value)

        begin = validate_code(handvorm_begin)
        einde = validate_code(handvorm_einde)

        with self.write_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")

            row = conn.execute(
                """
                SELECT subhndsh, final_subhndsh
                FROM dictionary_gloss
                WHERE id = ?
                """,
                (signbank_id,),
            ).fetchone()

            if row is None:
                raise ValueError("Gebaar niet gevonden in Signbank.")

            # Controleer of beide handvormcodes bestaan.
            for code in (begin, einde):
                if code == 0:
                    continue

                exists = conn.execute(
                    """
                    SELECT 1
                    FROM dictionary_fieldchoice
                    WHERE field = 'Handshape'
                      AND CAST(machine_value AS INTEGER) = ?
                    LIMIT 1
                    """,
                    (code,),
                ).fetchone()

                if exists is None:
                    raise ValueError(
                        f"Handvormcode {code} bestaat niet in Signbank."
                    )

            # Geen wijziging nodig.
            if (
                int(row["subhndsh"] or 0) == begin
                and int(row["final_subhndsh"] or 0) == einde
            ):
                return

            # Controleer de Signbank-gebruiker.
            user = conn.execute(
                "SELECT 1 FROM auth_user WHERE id = ?",
                (signbank_user_id,),
            ).fetchone()

            if user is None:
                raise ValueError("Signbank-gebruiker niet gevonden.")

            updated_at = timezone.localtime(
                timezone.now(),
                timezone=ZoneInfo("Europe/Brussels"),
            ).strftime("%Y-%m-%d %H:%M:%S.%f")

            conn.execute(
                """
                UPDATE dictionary_gloss
                SET subhndsh = ?,
                    final_subhndsh = ?,
                    lastUpdated = ?
                WHERE id = ?
                """,
                (begin, einde, updated_at, signbank_id),
            )

            conn.execute(
                """
                DELETE FROM dictionary_gloss_lastUpdater
                WHERE gloss_id = ?
                """,
                (signbank_id,),
            )

            conn.execute(
                """
                INSERT INTO dictionary_gloss_lastUpdater
                    (gloss_id, user_id)
                VALUES (?, ?)
                """,
                (signbank_id, signbank_user_id),
            )

        # Synchroniseer de gewijzigde handvormen naar VGT Studio.
        from django.core.management import call_command

        try:
            call_command(
                "sync_signbank",
                signbank_id=signbank_id,
                verbosity=0,
            )
        except Exception as exc:
            raise RuntimeError(
                "De handvormen zijn opgeslagen in Signbank, "
                "maar de synchronisatie naar VGT Studio is mislukt."
            ) from exc

    def update_locaties(self, signbank_id, locatie_begin, locatie_einde, signbank_user_id):
        """
        Wijzig de begin- en eindlocatie in de Signbank-master.
        """

        def validate_code(value):
            value = str(value or "0").strip()

            if not value.isdigit():
                raise ValueError("Ongeldige locatiecode.")

            return int(value)

        begin = validate_code(locatie_begin)
        einde = validate_code(locatie_einde)

        with self.write_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")

            row = conn.execute(
                """
                SELECT locprim, final_loc
                FROM dictionary_gloss
                WHERE id = ?
                """,
                (signbank_id,),
            ).fetchone()

            if row is None:
                raise ValueError("Gebaar niet gevonden in Signbank.")

            # Controleer of beide handvormcodes bestaan.
            for code in (begin, einde):
                if code == 0:
                    continue

                exists = conn.execute(
                    """
                    SELECT 1
                    FROM dictionary_fieldchoice
                    WHERE field = 'Location'
                      AND CAST(machine_value AS INTEGER) = ?
                    LIMIT 1
                    """,
                    (code,),
                ).fetchone()

                if exists is None:
                    raise ValueError(
                        f"Locatiecode {code} bestaat niet in Signbank."
                    )

            # Geen wijziging nodig.
            if (
                int(row["locprim"] or 0) == begin
                and int(row["final_loc"] or 0) == einde
            ):
                return

            # Controleer de Signbank-gebruiker.
            user = conn.execute(
                "SELECT 1 FROM auth_user WHERE id = ?",
                (signbank_user_id,),
            ).fetchone()

            if user is None:
                raise ValueError("Signbank-gebruiker niet gevonden.")

            updated_at = timezone.localtime(
                timezone.now(),
                timezone=ZoneInfo("Europe/Brussels"),
            ).strftime("%Y-%m-%d %H:%M:%S.%f")

            conn.execute(
                """
                UPDATE dictionary_gloss
                SET locprim = ?,
                    final_loc = ?,
                    lastUpdated = ?
                WHERE id = ?
                """,
                (begin, einde, updated_at, signbank_id),
            )

            conn.execute(
                """
                DELETE FROM dictionary_gloss_lastUpdater
                WHERE gloss_id = ?
                """,
                (signbank_id,),
            )

            conn.execute(
                """
                INSERT INTO dictionary_gloss_lastUpdater
                    (gloss_id, user_id)
                VALUES (?, ?)
                """,
                (signbank_id, signbank_user_id),
            )

        # Synchroniseer de gewijzigde handvormen naar VGT Studio.
        from django.core.management import call_command

        try:
            call_command(
                "sync_signbank",
                signbank_id=signbank_id,
                verbosity=0,
            )
        except Exception as exc:
            raise RuntimeError(
                "De locaties zijn opgeslagen in Signbank, "
                "maar de synchronisatie naar VGT Studio is mislukt."
            ) from exc
