import os
import sqlite3
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from recordings.models import SignbankEntry


SIGNBANK_DB_PATH = os.environ.get(
    "SIGNBANK_DB_PATH",
    "/home/vlaamseg/signbank/signbank.db",
)


class Command(BaseCommand):
    help = "Synchroniseer glossgegevens uit Signbank naar VGT Studio."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Lees Signbank en toon resultaat zonder Studio-database te wijzigen.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if not os.path.exists(SIGNBANK_DB_PATH):
            raise CommandError(
                f"Signbank database niet gevonden: {SIGNBANK_DB_PATH}"
            )

        self.stdout.write(
            f"Signbank database: {SIGNBANK_DB_PATH}"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - er wordt niets opgeslagen.")
            )

        connection = self.open_signbank_database()

        try:
            gloss_content_type_id = self.get_gloss_content_type_id(connection)

            rows = connection.execute(
                """
                SELECT
                    g.id,
                    g.annotation_idgloss,
                    g.domhndsh,
                    g.final_domhndsh,
                    g.locprim,
                    g.final_loc,
                    g.semField,
                    g.semField1,
                    g.semField2,
                    g.semField3,
                    g.semField4,
                    g.inWeb,
                    g.lastUpdated
                FROM dictionary_gloss g
                ORDER BY g.id
                """
            ).fetchall()

            total = len(rows)

            self.stdout.write(
                f"{total} Signbank entries gevonden."
            )

            created_count = 0
            updated_count = 0
            unchanged_count = 0
            error_count = 0

            for index, row in enumerate(rows, start=1):
                try:
                    signbank_id = row["id"]

                    translations = self.get_translations(
                        connection,
                        signbank_id,
                    )

                    labels = self.get_labels(
                        connection,
                        signbank_id,
                        gloss_content_type_id,
                    )

                    locatie_einde = self.get_final_location(
                        connection,
                        row["final_loc"],
                    )

                    defaults = {
                        "gloss": self.clean(row["annotation_idgloss"]),
                        "handvorm_begin": self.clean(row["domhndsh"]),
                        "handvorm_einde": self.clean(row["final_domhndsh"]),
                        "locatie_begin": self.clean(row["locprim"]),
                        "locatie_einde": locatie_einde,
                        "mogelijke_vertaling": translations,
                        "categorie_1": self.get_fieldchoice_label(
                            connection, "semField", row["semField"]
                        ),
                        "categorie_2": self.get_fieldchoice_label(
                            connection, "semField", row["semField1"]
                        ),
                        "categorie_3": self.get_fieldchoice_label(
                            connection, "semField", row["semField2"]
                        ),
                        "categorie_4": self.get_fieldchoice_label(
                            connection, "semField", row["semField3"]
                        ),
                        "categorie_5": self.get_fieldchoice_label(
                            connection, "semField", row["semField4"]
                        ),
                        "labels": labels,
                        "in_woordenboek": bool(row["inWeb"]),
                        "signbank_last_updated": self.parse_signbank_datetime(
                            row["lastUpdated"]
                        ),
                    }

                    if dry_run:
                        if index <= 10:
                            self.stdout.write(
                                f"{signbank_id}: "
                                f"{defaults['gloss']} | "
                                f"{defaults['mogelijke_vertaling']} | "
                                f"labels: {defaults['labels']}"
                            )
                        continue

                    entry, created = SignbankEntry.objects.get_or_create(
                        signbank_id=signbank_id,
                        defaults=defaults,
                    )

                    if created:
                        created_count += 1
                    else:
                        changed = False

                        for field, new_value in defaults.items():
                            old_value = getattr(entry, field)

                            if old_value != new_value:
                                setattr(entry, field, new_value)
                                changed = True

                        if changed:
                            entry.save()
                            updated_count += 1
                        else:
                            unchanged_count += 1

                except Exception as exc:
                    error_count += 1

                    self.stderr.write(
                        self.style.ERROR(
                            f"Fout bij Signbank ID {row['id']}: {exc}"
                        )
                    )

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Dry run voltooid. {total} entries gelezen."
                    )
                )
                return

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS("Synchronisatie voltooid.")
            )
            self.stdout.write(f"Nieuw:       {created_count}")
            self.stdout.write(f"Bijgewerkt:  {updated_count}")
            self.stdout.write(f"Ongewijzigd: {unchanged_count}")
            self.stdout.write(f"Fouten:      {error_count}")

        finally:
            connection.close()

    def open_signbank_database(self):
        """
        Open Signbank expliciet read-only.
        """
        uri = f"file:{SIGNBANK_DB_PATH}?mode=ro"

        connection = sqlite3.connect(
            uri,
            uri=True,
            timeout=30,
        )

        connection.row_factory = sqlite3.Row

        return connection

    def get_gloss_content_type_id(self, connection):
        """
        Zoek het content_type van dictionary.gloss.
        Dit is nodig omdat tagging_taggeditem een GenericForeignKey gebruikt.
        """
        row = connection.execute(
            """
            SELECT id
            FROM django_content_type
            WHERE app_label = 'dictionary'
              AND model = 'gloss'
            LIMIT 1
            """
        ).fetchone()

        if row:
            return row["id"]

        self.stdout.write(
            self.style.WARNING(
                "Content type dictionary.gloss niet gevonden. "
                "Labels worden voorlopig niet geïmporteerd."
            )
        )

        return None

    def get_translations(self, connection, gloss_id):
        """
        Verzamel alle mogelijke vertalingen van een gloss.
        Dubbele vertalingen worden verwijderd.
        """
        rows = connection.execute(
            """
            SELECT DISTINCT
                k.text
            FROM dictionary_translation t
            INNER JOIN dictionary_keyword k
                ON k.id = t.translation_id
            WHERE t.gloss_id = ?
              AND k.text IS NOT NULL
              AND TRIM(k.text) != ''
            ORDER BY k.text COLLATE NOCASE
            """,
            (gloss_id,),
        ).fetchall()

        translations = [
            self.clean(row["text"])
            for row in rows
            if self.clean(row["text"])
        ]

        return "; ".join(translations)

    def get_labels(
        self,
        connection,
        gloss_id,
        gloss_content_type_id,
    ):
        """
        Verzamel alle tags uit tagging_tag en sla ze in Studio op als labels.
        """
        if gloss_content_type_id is None:
            return ""

        rows = connection.execute(
            """
            SELECT DISTINCT
                tag.name
            FROM tagging_taggeditem item
            INNER JOIN tagging_tag tag
                ON tag.id = item.tag_id
            WHERE item.object_id = ?
              AND item.content_type_id = ?
              AND tag.name IS NOT NULL
              AND TRIM(tag.name) != ''
            ORDER BY tag.name COLLATE NOCASE
            """,
            (
                gloss_id,
                gloss_content_type_id,
            ),
        ).fetchall()

        labels = [
            self.clean(row["name"])
            for row in rows
            if self.clean(row["name"])
        ]

        return "; ".join(labels)

    def get_fieldchoice_label(self, connection, field_name, value):
        """
        Zet een machine_value uit dictionary_gloss om
        naar een leesbare Nederlandse waarde via dictionary_fieldchoice.
        """
        if value is None or str(value).strip() == "":
            return ""

        try:
            machine_value = int(value)
        except (TypeError, ValueError):
            return self.clean(value)

        row = connection.execute(
            """
            SELECT
                dutch_name,
                english_name
            FROM dictionary_fieldchoice
            WHERE field = ?
            AND machine_value = ?
            LIMIT 1
            """,
            (
                field_name,
                machine_value,
            ),
        ).fetchone()

        if not row:
            return str(value)

        return (
            self.clean(row["dutch_name"])
            or self.clean(row["english_name"])
            or str(value)
        )

    def get_final_location(self, connection, final_loc):
        """
        final_loc is in de oude Signbank een integer.

        Probeer eerst de leesbare waarde te vinden in dictionary_fieldchoice.
        Als er geen overeenkomst gevonden wordt, bewaren we de originele code.
        """
        if final_loc is None:
            return ""

        rows = connection.execute(
            """
            SELECT
                field,
                english_name,
                dutch_name,
                machine_value
            FROM dictionary_fieldchoice
            WHERE machine_value = ?
            """,
            (final_loc,),
        ).fetchall()

        if not rows:
            return str(final_loc)

        # Geef voorkeur aan een fieldchoice die over locatie gaat.
        for row in rows:
            field_name = self.clean(row["field"]).lower()

            if "loc" in field_name:
                return (
                    self.clean(row["dutch_name"])
                    or self.clean(row["english_name"])
                    or str(final_loc)
                )

        # Fallback wanneer machine_value wel gevonden wordt,
        # maar het veld niet herkenbaar "locatie" heet.
        if len(rows) == 1:
            return (
                self.clean(rows[0]["dutch_name"])
                or self.clean(rows[0]["english_name"])
                or str(final_loc)
            )

        return str(final_loc)

    def parse_signbank_datetime(self, value):
        if not value:
            return None

        if isinstance(value, datetime):
            dt = value
        else:
            dt = parse_datetime(str(value))

        if dt is None:
            return None

        if timezone.is_naive(dt):
            dt = timezone.make_aware(
                dt,
                timezone.get_current_timezone(),
            )

        return dt

    @staticmethod
    def clean(value):
        if value is None:
            return ""

        return str(value).strip()