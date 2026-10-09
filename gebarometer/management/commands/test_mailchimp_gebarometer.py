from django.core.management.base import BaseCommand

from gebarometer.mailchimp import MailChimpClient


class Command(BaseCommand):
    help = "Test de Mailchimp-pollkoppeling zonder databasewijzigingen."

    def handle(self, *args, **options):
        client = MailChimpClient.from_curl_file(
            "mailchimp_poll_curl.txt"
        )

        campaigns = client.get_recent_campaigns(
            "2bcc06d051"
        )

        self.stdout.write(
            f"Aantal recente campagnes: {len(campaigns)}"
        )

        self.stdout.write("")

        for campaign in campaigns:
            self.stdout.write(
                f"{campaign['publish_time']} | "
                f"{campaign['campaign_name']} | "
                f"{campaign['campaign_id']}"
            )