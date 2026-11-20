from urllib.parse import urlsplit

from django import forms
from django.core.validators import FileExtensionValidator


class EtymologyPairForm(forms.Form):
    source_type = forms.ChoiceField(
        choices=[
            ("keep", "Huidige video behouden"),
            ("vimeo", "Vimeo-link"),
            ("upload", "Video uploaden"),
            ("webcam", "Webcamopname"),
        ],
    )

    video_url = forms.URLField(
        required=False,
        max_length=2000,
    )

    video = forms.FileField(
        required=False,
        allow_empty_file=False,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "mp4",
                    "m4v",
                    "mov",
                    "webm",
                    "mkv",
                    "avi",
                    "mpeg",
                    "mpg",
                    "ogg",
                    "ogv",
                ],
            )
        ],
    )

    text = forms.CharField(
        label="Etymologietekst",
        strip=True,
        required=False,
        error_messages={
            "required": "Vul de tekst bij deze video in.",
        },
    )

    pair_number = forms.IntegerField(
        required=False,
        min_value=0,
    )

    published = forms.BooleanField(required=False)
    
    expected_revision = forms.RegexField(
        regex=r"^[0-9a-f]{64}$",
        required=False,
        error_messages={
            "invalid": "De paargegevens zijn ongeldig. Laad ze opnieuw.",
        },
    )

    def clean_video(self):
        video = self.cleaned_data.get("video")

        if video and video.size > 250 * 1024 * 1024:
            raise forms.ValidationError(
                "De video mag maximaal 250 MB groot zijn."
            )

        return video

    def clean(self):
        data = super().clean()

        source_type = data.get("source_type")
        pair_number = data.get("pair_number")
        video = data.get("video")
        video_url = data.get("video_url", "")

        if (
            pair_number is not None
            and not data.get("expected_revision")
        ):
            self.add_error(
                "expected_revision",
                "Laad het etymologiepaar opnieuw voordat je opslaat.",
            )

        if source_type == "keep":
            if pair_number is None:
                self.add_error(
                    "source_type",
                    "Voeg eerst een video of Vimeo-link toe.",
                )

            if video or video_url:
                self.add_error(
                    "source_type",
                    "Kies het juiste videotype voor de nieuwe video.",
                )

        elif source_type == "vimeo":
            if not video_url:
                self.add_error(
                    "video_url",
                    "Vul een Vimeo-link in.",
                )
            else:
                parsed = urlsplit(video_url)

                if (
                    parsed.scheme not in {"http", "https"}
                    or parsed.hostname not in {
                        "vimeo.com",
                        "www.vimeo.com",
                        "player.vimeo.com",
                    }
                    or parsed.username
                    or parsed.password
                ):
                    self.add_error(
                        "video_url",
                        "Gebruik een geldige Vimeo-link.",
                    )

            if video:
                self.add_error(
                    "video",
                    "Kies video-upload of webcam om dit bestand te bewaren.",
                )

        elif source_type in {"upload", "webcam"}:
            if not video and "video" not in self.errors:
                self.add_error(
                    "video",
                    "Kies een video of maak eerst een webcamopname.",
                )

            if video_url:
                self.add_error(
                    "video_url",
                    "Gebruik bij upload of webcam geen Vimeo-link.",
                )

        return data