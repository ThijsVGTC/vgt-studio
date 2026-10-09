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

        results = client.get_gebarometer_results(
            campaign["report_id"]
        )

        from gebarometer.models import GebarometerItem

        item = (
            GebarometerItem.objects
            .filter(
                historical_gloss__iexact=campaign["campaign_name"],
            )
            .order_by("-planned_date")
            .first()
        )

        self.stdout.write(
            f"Campagne: {campaign['campaign_name']}"
        )

        self.stdout.write(
            f"Campaign ID: {campaign['campaign_id']}"
        )

        self.stdout.write(
            f"Report ID: {campaign['report_id']}"
        )

        self.stdout.write(
            f"Poll ID: {results['poll_id']}"
        )

        self.stdout.write(
            f"Resultaten: "
            f"{results['ja_ja']} / "
            f"{results['ja_nee']} / "
            f"{results['nee']} / "
            f"{results['twijfel']} "
            f"(totaal {results['total_votes']})"
        )

        if item:
            self.stdout.write(
                self.style.SUCCESS(
                    f"GebarometerItem gevonden: "
                    f"ID {item.id} - "
                    f"{item.historical_gloss} - "
                    f"{item.planned_date}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Geen GebarometerItem gevonden."
                )
            )