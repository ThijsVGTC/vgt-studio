import os

from django.core.management.base import BaseCommand, CommandError

from gebarometer.mailchimp import MailChimpClient, MailChimpAPIError


class Command(BaseCommand):
    help = "Test de Mailchimp-koppeling voor Gebarometer zonder databasewijzigingen."

    def handle(self, *args, **options):
        client = MailChimpClient.from_curl_file(
            "mailchimp_curl.txt"
        )

        result = client.test_advanced_report(
            "11042816"
        )

        self.stdout.write(
            f"Status: {result['status_code']}"
        )

        self.stdout.write(
            f"URL: {result['url']}"
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