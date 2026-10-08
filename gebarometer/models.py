from django.db import models
from recordings.models import SignbankEntry


class GebarometerItem(models.Model):

    MAILCHIMP_STATUS_CHOICES = [
        ("NIET_VERSTUURD", "Niet verstuurd"),
        ("GEPLAND", "Gepland"),
        ("VERSTUURD", "Verstuurd"),
    ]

    signbank_entry = models.ForeignKey(
        SignbankEntry,
        on_delete=models.PROTECT,
        related_name="gebarometer_items",
        null=True,
        blank=True,
    )

    historical_gloss = models.CharField(
        max_length=255,
        blank=True,
    )

    planned_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
    )

    position = models.PositiveIntegerField(
        default=0,
    )

    mailchimp_status = models.CharField(
        max_length=20,
        choices=MAILCHIMP_STATUS_CHOICES,
        default="NIET_VERSTUURD",
    )

    mailchimp_report_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
    )

    mailchimp_url = models.URLField(
        max_length=1000,
        blank=True,
    )

    total_votes = models.PositiveIntegerField(
        default=0,
    )

    ja_ja = models.PositiveIntegerField(
        default=0,
    )

    ja_nee = models.PositiveIntegerField(
        default=0,
    )

    nee = models.PositiveIntegerField(
        default=0,
    )

    twijfel = models.PositiveIntegerField(
        default=0,
    )

    oost_vlaanderen = models.PositiveIntegerField(
        default=0,
    )

    west_vlaanderen = models.PositiveIntegerField(
        default=0,
    )

    vlaams_brabant = models.PositiveIntegerField(
        default=0,
    )

    antwerpen = models.PositiveIntegerField(
        default=0,
    )

    limburg = models.PositiveIntegerField(
        default=0,
    )

    remarks = models.TextField(
        blank=True,
    )

    internal_remarks = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["planned_date", "position", "id"]

    def __str__(self):
        gloss = (
            self.signbank_entry.gloss
            if self.signbank_entry
            else self.historical_gloss or "Onbekende gloss"
        )

        return f"{gloss} - {self.planned_date}"