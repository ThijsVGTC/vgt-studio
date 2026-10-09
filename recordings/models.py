from django.db import models
from urllib.parse import urlparse
import os
# Create your models here.

class SignbankEntry(models.Model):
    signbank_id = models.IntegerField(
        unique=True,
        db_index=True,
    )

    gloss = models.CharField(
        max_length=255,
        blank=True,
    )

    handvorm_begin_code = models.CharField(
        max_length=50,
        blank=True,
    )

    handvorm_einde_code = models.CharField(
        max_length=50,
        blank=True,
    )

    locatie_begin_code = models.CharField(
        max_length=50,
        blank=True,
    )

    locatie_einde_code = models.CharField(
        max_length=50,
        blank=True,
    )

    handvorm_begin = models.CharField(
        max_length=50,
        blank=True,
    )

    handvorm_einde = models.CharField(
        max_length=50,
        blank=True,
    )

    locatie_begin = models.CharField(
        max_length=100,
        blank=True,
    )

    locatie_einde = models.CharField(
        max_length=100,
        blank=True,
    )

    mogelijke_vertaling = models.TextField(
        blank=True,
    )

    categorie_1 = models.CharField(
        max_length=50,
        blank=True,
    )

    categorie_2 = models.CharField(
        max_length=50,
        blank=True,
    )

    categorie_3 = models.CharField(
        max_length=50,
        blank=True,
    )

    categorie_4 = models.CharField(
        max_length=50,
        blank=True,
    )

    categorie_5 = models.CharField(
        max_length=50,
        blank=True,
    )

    variants = models.JSONField(
        default=list,
        blank=True,
    )

    labels = models.TextField(
        blank=True,
    )

    thumbnail_path = models.CharField(
        max_length=500,
        blank=True,
    )

    video_hash = models.CharField(
        max_length=64,
        blank=True,
    )

    opmerkingen = models.JSONField(
        default=list,
        blank=True,
    )

    etymologie = models.JSONField(
        default=list,
        blank=True,
    )

    bronnen = models.JSONField(
        default=list,
        blank=True,
    )

    in_woordenboek = models.BooleanField(
        default=False,
    )

    signbank_last_updated = models.DateTimeField(
        null=True,
        blank=True,
    )

    synced_at = models.DateTimeField(
        auto_now=True,
    )

    @property
    def handvorm_begin_image(self):
        if not self.handvorm_begin_code or self.handvorm_begin_code == "0":
            return ""
        
        return (
            "recordings/images/handshapes/"
            f"handshape_{self.handvorm_begin_code}.png"
        )


    @property
    def handvorm_einde_image(self):
        if not self.handvorm_einde_code or self.handvorm_einde_code == "0":
            return ""

        return (
            "recordings/images/handshapes/"
            f"handshape_{self.handvorm_einde_code}.png"
        )
    
    @property
    def video_url(self):
        if not self.gloss or not self.signbank_id:
            return ""

        prefix = self.gloss[:2].upper()

        return (
            "https://vlaamsegebarentaal.be/signbank/"
            "dictionary/protected_media/glossvideo/"
            f"{prefix}/{self.gloss}-{self.signbank_id}.mp4"
        )

    @property
    def variant_badges(self):
        abbreviations = {
            "West-Vlaanderen": "WVL",
            "Oost-Vlaanderen": "OVL",
            "Antwerpen": "ANT",
            "Limburg": "LIM",
            "Vlaams-Brabant": "VBR",
            "Vlaanderen": "VL",
            "nog niet gekend": "?",
        }

        return [
            {
                "name": variant,
                "short": abbreviations.get(variant, variant),
            }
            for variant in self.variants
        ]
    
    @property
    def thumbnail_url(self):
        if not self.thumbnail_path:
            return ""

        return f"/media/{self.thumbnail_path}"
    
    @property
    def label_list(self):
        if not self.labels:
            return []

        return [
            label.strip()
            for label in self.labels.split(";")
            if label.strip()
        ]

    @property
    def functional_labels(self):
        mapping = {
            "expliciet": ("Ex", "Expliciet"),
            "verouderd": ("Vo", "Verouderd"),
            "beledigend": ("Be", "Beledigend"),
            "neologisme": ("Nl", "Neologisme"),
            "negatief": ("Ne", "Negatief"),
        }

        result = []

        for label in self.label_list:
            key = label.strip().lower()

            if key in mapping:
                short, name = mapping[key]
                result.append({
                    "short": short,
                    "name": name,
                })

        return result


    @property
    def internal_labels(self):
        functional = {
            "expliciet",
            "verouderd",
            "beledigend",
            "neologisme",
            "negatief",
        }

        return [
            label
            for label in self.label_list
            if label.strip().lower() not in functional
        ]

    def __str__(self):
        return f"{self.gloss} ({self.signbank_id})"
    
class RecordingItem(models.Model):
    REVIEW_CHOICES = [
        ("OPGENOMEN", "OPGENOMEN"),
        ("OVER-OPM", "OVER-OPM"),
        ("OVER-AL_VIDEO", "OVER-AL_VIDEO"),
        ("OPNAME_AFGEKEURD", "OPNAME AFGEKEURD"),
    ]
    signbank_id = models.IntegerField(unique=True)
    signbank_entry = models.ForeignKey(SignbankEntry,on_delete=models.SET_NULL,null=True,blank=True,related_name="recording_items",)
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
    signbank_exported_at = models.DateTimeField(blank=True,null=True,) 
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

    @property
    def signbank_video_url(self):
        if self.signbank_entry:
            return self.signbank_entry.video_url

        return self.old_video_url

    @property
    def signbank_thumbnail_path(self):
        if self.signbank_entry and self.signbank_entry.thumbnail_path:
            return self.signbank_entry.thumbnail_path

        return self.thumbnail_path    

    def __str__(self):
        return f"{self.gloss_id} ({self.signbank_id})"

class RecordingSeries(models.Model):
    STATUS_CHOICES = [
        ("ACTIEF", "Actief"),
        ("ONDERBROKEN", "Onderbroken"),
        ("VOLTOOID", "Voltooid"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIEF",
    )

    current_index = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Opnamereeks {self.pk}"

class RecordingSeriesItem(models.Model):
    series = models.ForeignKey(
        RecordingSeries,
        on_delete=models.CASCADE,
        related_name="items",
    )

    recording_item = models.ForeignKey(
        RecordingItem,
        on_delete=models.CASCADE,
        related_name="series_items",
    )

    position = models.PositiveIntegerField()

    processed = models.BooleanField(
        default=False,
    )

    skipped = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["position"]

        constraints = [
            models.UniqueConstraint(
                fields=["series", "position"],
                name="unique_recording_series_position",
            ),
            models.UniqueConstraint(
                fields=["series", "recording_item"],
                name="unique_recording_item_per_series",
            ),
        ]

    def __str__(self):
        return (
            f"Reeks {self.series_id} - "
            f"{self.position} - "
            f"{self.recording_item}"
        )

class AppSettings(models.Model):

    google_sheet_url = models.URLField(

        max_length=1000,

        blank=True

    )

    def __str__(self):

        return "VGT Studio instellingen"

class AllowedGoogleEmail(models.Model):
    email = models.EmailField(unique=True)
    active = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["email"]
        verbose_name = "Toegelaten Google-account"
        verbose_name_plural = "Toegelaten Google-accounts"

    def __str__(self):
        return self.email

class SignbankSyncLog(models.Model):
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(auto_now_add=True)

    total_entries = models.PositiveIntegerField(default=0)
    created_entries = models.PositiveIntegerField(default=0)
    updated_entries = models.PositiveIntegerField(default=0)
    unchanged_entries = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)

    successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-finished_at"]

    @property
    def duration_seconds(self):
        if not self.started_at or not self.finished_at:
            return None

        return round(
            (self.finished_at - self.started_at).total_seconds(),
            1,
        )

    def __str__(self):
        return f"Signbank sync {self.finished_at:%Y-%m-%d %H:%M}"