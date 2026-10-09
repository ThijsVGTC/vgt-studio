from django.core.management.base import BaseCommand

from gebarometer.mailchimp import MailChimpClient
from gebarometer.models import GebarometerItem


class Command(BaseCommand):
    help = "Synchroniseer recente Mailchimp-campagnes met Gebarometer."

    def handle(self, *args, **options):
        client = MailChimpClient.from_curl_file(
            "mailchimp_poll_curl.txt"
        )

        campaigns = client.get_recent_campaigns(
            "2bcc06d051"
        )

        updated = 0
        skipped = 0
        not_found = 0
        errors = 0

        for recent in campaigns:
            campaign_id = recent["campaign_id"]

            try:
                campaign = client.get_campaign_overview(
                    campaign_id
                )

                if (
                    campaign["list_name"] != "Gebarometer"
                    or not campaign["has_polls"]
                ):
                    skipped += 1
                    continue

                item = (
                    GebarometerItem.objects
                    .filter(
                        historical_gloss__iexact=campaign[
                            "campaign_name"
                        ],
                    )
                    .order_by("-planned_date")
                    .first()
                )

                if not item:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Niet gevonden: "
                            f"{campaign['campaign_name']}"
                        )
                    )
                    not_found += 1
                    continue

                results = client.get_gebarometer_results(
                    campaign["report_id"]
                )

                item.mailchimp_campaign_id = campaign[
                    "campaign_id"
                ]
                item.mailchimp_report_id = campaign[
                    "report_id"
                ]
                item.mailchimp_url = campaign[
                    "report_url"
                ]

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

                updated += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"OK: "
                        f"{campaign['campaign_name']} "
                        f"({item.planned_date})"
                    )
                )

            except Exception as exc:
                errors += 1

                self.stderr.write(
                    self.style.ERROR(
                        f"Fout bij {campaign_id}: {exc}"
                    )
                )

        self.stdout.write("")
        self.stdout.write("Synchronisatie voltooid.")
        self.stdout.write(f"Bijgewerkt: {updated}")
        self.stdout.write(f"Overgeslagen: {skipped}")
        self.stdout.write(f"Niet gevonden: {not_found}")
        self.stdout.write(f"Fouten: {errors}")