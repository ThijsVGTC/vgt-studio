import os

from django.core.management.base import BaseCommand, CommandError

from gebarometer.mailchimp import MailChimpClient, MailChimpAPIError


class Command(BaseCommand):
    help = "Test de Mailchimp-koppeling voor Gebarometer zonder databasewijzigingen."

    def handle(self, *args, **options):
        client = MailChimpClient.from_curl_file(
            "/tmp/mailchimp_curl.txt"
        )

        cookie_value = client.session.headers.get("cookie", "")

        if not cookie_value:
            raise CommandError(
                "Cookie kon niet uit de cURL gelezen worden."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Cookie correct ingelezen ({len(cookie_value)} tekens)."
            )
        )

        self.stdout.write(
            f"Aantal headers: {len(client.session.headers)}"
        )