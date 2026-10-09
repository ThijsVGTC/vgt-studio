from django.core.management.base import BaseCommand

from gebarometer.mailchimp import MailChimpClient


class Command(BaseCommand):
    help = "Test de Mailchimp-pollkoppeling zonder databasewijzigingen."

    def handle(self, *args, **options):
        client = MailChimpClient.from_curl_file(
            "mailchimp_poll_curl.txt"
        )

        campaign = client.get_campaign_overview(
            "2bcc06d051"
        )

        self.stdout.write(
            f"Campaign ID: {campaign['campaign_id']}"
        )

        self.stdout.write(
            f"Report ID: {campaign['report_id']}"
        )

        self.stdout.write(
            f"Naam: {campaign['campaign_name']}"
        )

        self.stdout.write(
            f"Verzendtijd: {campaign['send_time']}"
        )

        self.stdout.write(
            f"Status: {campaign['status']}"
        )

        self.stdout.write(
            f"Heeft poll: {campaign['has_polls']}"
        )

        self.stdout.write(
            f"Report URL: {campaign['report_url']}"
        )