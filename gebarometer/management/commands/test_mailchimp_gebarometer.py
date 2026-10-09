from django.core.management.base import BaseCommand

from gebarometer.mailchimp import MailChimpClient


class Command(BaseCommand):
    help = "Test de Mailchimp-pollkoppeling zonder databasewijzigingen."

    def handle(self, *args, **options):
        client = MailChimpClient.from_curl_file(
            "mailchimp_poll_curl.txt"
        )

        results = client.get_gebarometer_results(
            "11042816"
        )

        self.stdout.write(
            f"Poll ID: {results['poll_id']}"
        )

        self.stdout.write(
            f"JA-JA: {results['ja_ja']}"
        )

        self.stdout.write(
            f"JA-NEE: {results['ja_nee']}"
        )

        self.stdout.write(
            f"NEE: {results['nee']}"
        )

        self.stdout.write(
            f"Twijfel: {results['twijfel']}"
        )

        self.stdout.write(
            f"Totaal: {results['total_votes']}"
        )