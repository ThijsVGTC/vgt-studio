from django import forms

class NewSignbankEntryForm(forms.Form):
    gloss = forms.CharField(
        label="GLOSS",
        max_length=30,
        strip=True,
        required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "Bijvoorbeeld: VOORBEELD-A",
            "autocomplete": "off",
        }),
    )

    translation = forms.CharField(
        label="Nederlandse vertaling",
        max_length=100,
        strip=True,
        required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "Mogelijke Nederlandse vertaling",
        }),
    )

    video = forms.FileField(
        label="Video",
        required=True,
        allow_empty_file=False,
        widget=forms.FileInput(attrs={
            "accept": "video/*",
        }),
        error_messages={
            "required": (
                "Upload een video of maak een webcamopname."
            ),
            "empty": (
                "De video is leeg. Selecteer een andere video "
                "of maak een nieuwe opname."
            ),
        },
    )

    def clean_gloss(self):
        gloss = self.cleaned_data["gloss"]

        if gloss in {".", ".."} or any(
            character in gloss
            for character in ("/", "\\", "\x00")
        ):
            raise forms.ValidationError(
                "De GLOSS mag geen schuine strepen "
                "of ongeldige bestandsnaamtekens bevatten."
            )

        return gloss