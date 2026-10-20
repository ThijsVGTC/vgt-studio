import os
import sqlite3

from django.core.management.base import BaseCommand, CommandError
from recordings.models import SignbankUser


SIGNBANK_DB_PATH = os.environ.get(
    "SIGNBANK_DB_PATH",
    "/app/signbank/signbank.db",
)


class Command(BaseCommand):
    help = "Synchroniseer alle Signbank-gebruikers naar VGT Studio."

    def handle(self, *args, **options):

        if not os.path.exists(SIGNBANK_DB_PATH):
            raise CommandError(
                f"Signbank database niet gevonden: {SIGNBANK_DB_PATH}"
            )

        connection = sqlite3.connect(
            f"file:{SIGNBANK_DB_PATH}?mode=ro",
            uri=True,
        )
        connection.row_factory = sqlite3.Row

        try:
            users = connection.execute(
                """
                SELECT
                    id,
                    username,
                    email,
                    first_name,
                    last_name,
                    is_active
                FROM auth_user
                """
            ).fetchall()
        finally:
            connection.close()

        created = 0
        updated = 0

        for user in users:

            obj, was_created = SignbankUser.objects.update_or_create(
                signbank_id=user["id"],
                defaults={
                    "username": user["username"],
                    "email": user["email"] or "",
                    "first_name": user["first_name"] or "",
                    "last_name": user["last_name"] or "",
                    "is_active": bool(user["is_active"]),
                },
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Signbank-gebruikers gesynchroniseerd: "
                f"{created} nieuw, {updated} bijgewerkt."
            )
        )