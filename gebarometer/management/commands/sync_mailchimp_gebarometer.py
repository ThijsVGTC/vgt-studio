from django.core.management.base import BaseCommand, CommandError

from gebarometer.mailchimp import MailChimpClient
from gebarometer.models import GebarometerItem


class Command(BaseCommand):
    help = "Synchroniseer één Mailchimp-campagne met Gebarometer."

    def add_arguments(self, parser):
        parser.add_argument(
            "campaign_id",
            type=str,
            help="Moderne Mailchimp campaign ID, bv. 2bcc06d051",
        )

    def handle(self, *args, **options):
        campaign_id = options["campaign_id"]

        client = MailChimpClient.from_curl_file(
            "mailchimp_poll_curl.txt"
        )

        campaign = client.get_campaign_overview(
            campaign_id
        )

        if not campaign["campaign_name"]:
            raise CommandError(
                "Geen campagnenaam gevonden."
            )

        if not campaign["report_id"]:
            raise CommandError(
                "Geen legacy report ID gevonden."
            )

        item = (
            GebarometerItem.objects
            .filter(
                historical_gloss__iexact=campaign["campaign_name"],
            )
            .order_by("-planned_date")
            .first()
        )

        if not item:
            raise CommandError(
                f"Geen GebarometerItem gevonden voor "
                f"{campaign['campaign_name']}."
            )

        results = client.get_gebarometer_results(
            campaign["report_id"]
        )

        item.mailchimp_campaign_id = campaign["campaign_id"]
        item.mailchimp_report_id = campaign["report_id"]
        item.mailchimp_url = campaign["report_url"]

        if campaign["status"] == "sent":
            item.mailchimp_status = "VERSTUURD"
        else:
            item.mailchimp_status = "NIET_VERSTUURD"

        item.total_votes = results["total_votes"]
        item.ja_ja = results["ja_ja"]
        item.ja_nee = results["ja_nee"]
        item.nee = results["nee"]
        item.twijfel = results["twijfel"]

        item.save(
            update_fields=[
                "mailchimp_campaign_id",
                "mailchimp_report_id",
                "mailchimp_url",
                "mailchimp_status",
                "total_votes",
                "ja_ja",
                "ja_nee",
                "nee",
                "twijfel",
                "updated_at",
            ]
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Gesynchroniseerd: "
                f"{item.historical_gloss} "
                f"({item.planned_date})"
            )
        )

        self.stdout.write(
            f"Resultaten: "
            f"{item.ja_ja} / "
            f"{item.ja_nee} / "
            f"{item.nee} / "
            f"{item.twijfel} "
            f"(totaal {item.total_votes})"
        )