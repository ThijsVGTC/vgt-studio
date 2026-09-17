from django.db import models
from urllib.parse import urlparse
import os
# Create your models here.
class RecordingItem(models.Model):
    REVIEW_CHOICES = [
        ("OPGENOMEN", "OPGENOMEN"),
        ("OVER-OPM", "OVER-OPM"),
        ("OVER-AL_VIDEO", "OVER-AL_VIDEO"),
    ]
    signbank_id = models.IntegerField(unique=True)
    gloss_id = models.CharField(max_length=255)
    old_video_url = models.URLField(
        max_length=1000,
        blank=True
    )

    status = models.CharField(
        max_length=255,
        blank=True
    )
    recording_by = models.CharField(
        max_length=255,
        blank=True
    )

    recording_date = models.CharField(
        max_length=100,
        blank=True
    )

    remarks = models.TextField(
        blank=True
    )

    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_CHOICES,
        blank=True,
        default="",
    )
    
    @property
    def filename(self):

        if not self.old_video_url:
            return ""

        return os.path.basename(
            urlparse(self.old_video_url).path
        )

    def __str__(self):
        return f"{self.gloss_id} ({self.signbank_id})"

class AppSettings(models.Model):

    google_sheet_url = models.URLField(

        max_length=1000,

        blank=True

    )

    def __str__(self):

        return "VGT Studio instellingen"