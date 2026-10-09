from django.core.management.base import BaseCommand

from gebarometer.mailchimp import MailChimpClient


class Command(BaseCommand):
    help = "Test de Mailchimp-pollkoppeling zonder databasewijzigingen."

    def handle(self, *args, **options):
        client = MailChimpClient.from_curl_file(
            "mailchimp_poll_curl.txt"
        )

        result = client.test_advanced_report(
            "11042816"
        )

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