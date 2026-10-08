import os

from django.core.management.base import BaseCommand, CommandError

from gebarometer.mailchimp import MailChimpClient, MailChimpAPIError


class Command(BaseCommand):
    help = "Test de Mailchimp-koppeling voor Gebarometer zonder databasewijzigingen."

    def handle(self, *args, **options):
        cookie = os.environ.get("MAILCHIMP_COOKIE")

        if not cookie:
            raise CommandError(
                "Environment variable MAILCHIMP_COOKIE ontbreekt."
            )

        client = MailChimpClient(cookie)

        result = client.test_advanced_report("11042816")

        self.stdout.write(
            f"Status: {result['status_code']}"
        )

        self.stdout.write(
            f"Content-Type: {result['content_type']}"
        )

        self.stdout.write(
            f"Redirect: {result['location']}"
        )

        self.stdout.write("")
        self.stdout.write("Eerste response:")
        self.stdout.write(result["text"])