from django.db import models
from urllib.parse import urlparse
import os
# Create your models here.
class RecordingItem(models.Model):
    REVIEW_CHOICES = [
        ("OPGENOMEN", "OPGENOMEN"),
        ("OVER-OPM", "OVER-OPM"),
        ("OVER-AL_VIDEO", "OVER-AL_VIDEO"),
        ("OPNAME_AFGEKEURD", "OPNAME AFGEKEURD"),
    ]
    signbank_id = models.IntegerField(unique=True)
    gloss_id = models.CharField(max_length=255)
    old_video_url = models.URLField(
        max_length=1000,
        blank=True
    )
    thumbnail_path = models.CharField(max_length=500, blank=True,)
    video_hash = models.CharField(max_length=64,blank=True,)
    new_video = models.FileField(upload_to="recordings/new/",blank=True,null=True,)
    rejected_video = models.FileField(upload_to="recordings/rejected/",blank=True,null=True,)
    VIDEO_REVIEW_CHOICES = [("WACHT_OP_CONTROLE", "Wacht op controle"),("GOEDGEKEURD", "Goedgekeurd"),("AFGEKEURD", "Afgekeurd"),]
    new_video_status = models.CharField(max_length=30,choices=VIDEO_REVIEW_CHOICES,blank=True,default="",)  
    video_review_remarks = models.TextField(blank=True,default="",)
    signbank_exported = models.BooleanField(default=False,)    
    status = models.CharField(max_length=255,blank=True)
    recording_by = models.CharField(max_length=255,blank=True)
    recording_date = models.CharField(max_length=100,blank=True)
    remarks = models.TextField(blank=True)
    review_status = models.CharField(max_length=20,choices=REVIEW_CHOICES,blank=True,default="",)
    
    @property
    def filename(self):

        if not self.old_video_url:
            return ""

        return os.path.basename(
            urlparse(self.old_video_url).path
        )

    @property
    def thumbnail_url(self):
        if not self.thumbnail_path:
            return ""
        return f"/media/{self.thumbnail_path}"

    def __str__(self):
        return f"{self.gloss_id} ({self.signbank_id})"

class AppSettings(models.Model):

    google_sheet_url = models.URLField(

        max_length=1000,

        blank=True

    )

    def __str__(self):

        return "VGT Studio instellingen"