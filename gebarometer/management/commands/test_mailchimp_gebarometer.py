from django.core.management.base import BaseCommand

from gebarometer.mailchimp import MailChimpClient


class Command(BaseCommand):
    help = "Test de Mailchimp-pollkoppeling zonder databasewijzigingen."

    def handle(self, *args, **options):
        client = MailChimpClient.from_curl_file(
            "mailchimp_poll_curl.txt"
        )

        poll = client.get_poll(
            "11042816"
        )

        self.stdout.write(
            f"Poll ID: {poll['poll_id']}"
        )

        self.stdout.write("")

        for option in poll["options"]:
            self.stdout.write(
                f"{option['id']} | "
                f"{option['value']} | "
                f"{option['votes']} stemmen"
            )