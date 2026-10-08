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

        try:
            reports = client.get_reports()
        except MailChimpAPIError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Mailchimp bereikbaar. {len(reports)} campagnes gevonden."
            )
        )

        if not reports:
            return

        report = reports[0]

        report_id = (
            report.get("id")
            or report.get("campaign_id")
            or report.get("report_id")
        )

        title = (
            report.get("title")
            or report.get("subject")
            or report.get("campaign_title")
            or "Onbekende campagne"
        )

        self.stdout.write("")
        self.stdout.write(f"Eerste campagne: {title}")
        self.stdout.write(f"Report ID: {report_id}")
        self.stdout.write(
            f"Verzenddatum: {client.parse_send_date(report)}"
        )

        if not report_id:
            self.stdout.write(
                self.style.WARNING(
                    "Geen report_id gevonden in deze campagne."
                )
            )
            return

        try:
            poll = client.get_poll(report_id)
        except MailChimpAPIError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write("")
        self.stdout.write(f"Poll ID: {poll['poll_id']}")

        for option in poll["options"]:
            self.stdout.write(
                f"- {option['value']}: {option['votes']} stemmen"
            )