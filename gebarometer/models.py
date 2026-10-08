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

    @property
    def ja_ja_percentage(self):
        if not self.total_votes:
            return 0
        return round((self.ja_ja / self.total_votes) * 100, 1)


    @property
    def ja_nee_percentage(self):
        if not self.total_votes:
            return 0
        return round((self.ja_nee / self.total_votes) * 100, 1)


    @property
    def nee_percentage(self):
        if not self.total_votes:
            return 0
        return round((self.nee / self.total_votes) * 100, 1)


    @property
    def twijfel_percentage(self):
        if not self.total_votes:
            return 0
        return round((self.twijfel / self.total_votes) * 100, 1)


    @property
    def result_is_positive(self):
        if not self.total_votes:
            return None

        positive_votes = self.ja_ja + self.ja_nee

        return (positive_votes / self.total_votes) >= 0.67

    def __str__(self):
        gloss = (
            self.signbank_entry.gloss
            if self.signbank_entry
            else self.historical_gloss or "Onbekende gloss"
        )

        return f"{gloss} - {self.planned_date}"