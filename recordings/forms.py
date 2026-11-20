from django import forms


class TextListField(forms.Field):
    widget = forms.MultipleHiddenInput

    def __init__(self, *args, max_length=None, **kwargs):
        self.max_length = max_length
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value is None:
            return []

        if not isinstance(value, (list, tuple)):
            raise forms.ValidationError("Ongeldige lijst ontvangen.")

        result = []
        seen = set()

        for item in value:
            text = str(item).strip()

            if not text:
                raise forms.ValidationError(
                    "Vul lege regels in of verwijder ze uit de lijst."
                )

            if self.max_length and len(text) > self.max_length:
                raise forms.ValidationError(
                    f"Elke tekst mag maximaal "
                    f"{self.max_length} tekens bevatten."
                )

            key = text.casefold()

            if key in seen:
                raise forms.ValidationError(
                    "Dezelfde tekst staat meerdere keren in de lijst."
                )

            seen.add(key)
            result.append(text)

        return result


class NewSignbankEntryForm(forms.Form):
    gloss = forms.CharField(
        label="GLOSS",
        max_length=30,
        strip=True,
        required=True,
    )

    in_woordenboek = forms.TypedChoiceField(
        label="In woordenboek",
        choices=[
            ("0", "Nee"),
            ("1", "Ja"),
        ],
        coerce=lambda value: value == "1",
        empty_value=False,
    )

    handvorm_begin = forms.ChoiceField(
        label="Handvorm begin",
        required=False,
    )

    handvorm_einde = forms.ChoiceField(
        label="Handvorm einde",
        required=False,
    )

    locatie_begin = forms.ChoiceField(
        label="Locatie begin",
        required=False,
    )

    locatie_einde = forms.ChoiceField(
        label="Locatie einde",
        required=False,
    )

    translations = TextListField(
        label="Mogelijke vertalingen",
        max_length=100,
        required=True,
        error_messages={
            "required": "Voeg minstens één mogelijke vertaling toe.",
        },
    )

    categories = forms.MultipleChoiceField(
        label="Categorieën",
        required=False,
    )

    variants = forms.MultipleChoiceField(
        label="Varianten",
        required=False,
    )

    functional_labels = forms.MultipleChoiceField(
        label="Functionele labels",
        required=False,
    )

    internal_labels = forms.MultipleChoiceField(
        label="Interne labels",
        required=False,
    )

    comments = TextListField(
        label="Opmerkingen",
        required=False,
    )

    etymology = forms.URLField(
        label="Etymologievideo",
        required=False,
    )

    etymology_text = forms.CharField(
        label="Etymologietekst",
        widget=forms.Textarea,
        strip=True,
        required=False,
    )

    sources = TextListField(
        label="Bronnen",
        max_length=100,
        required=False,
    )

    video = forms.FileField(
        label="Video",
        required=True,
        allow_empty_file=False,
        widget=forms.FileInput(attrs={
            "accept": "video/*",
        }),
        error_messages={
            "required": "Upload een video of maak een webcamopname.",
            "empty": (
                "De video is leeg. Selecteer een andere video "
                "of maak een nieuwe opname."
            ),
        },
    )

    def __init__(self, *args, service=None, **kwargs):
        super().__init__(*args, **kwargs)
        required_fields = {
            "handvorm_begin": "Kies een handvorm voor het begin.",
            "handvorm_einde": "Kies een handvorm voor het einde.",
            "locatie_begin": "Kies een locatie voor het begin.",
            "locatie_einde": "Kies een locatie voor het einde.",
            "categories": "Voeg minstens één categorie toe.",
        }

        for field_name, message in required_fields.items():
            self.fields[field_name].required = True
            self.fields[field_name].error_messages["required"] = message

        if service is None:
            from .services.signbank_service import SignbankService
            service = SignbankService()

        handshape_choices = [
            ("", "Kies handvorm"),
        ] + [
            (str(item["code"]), item["name"])
            for item in service.get_handshape_choices()
        ]

        location_choices = [
            ("", "Kies locatie"),
        ] + [
            (str(item["code"]), item["name"])
            for item in service.get_location_choices()
        ]

        self.fields["handvorm_begin"].choices = handshape_choices
        self.fields["handvorm_einde"].choices = handshape_choices

        self.fields["locatie_begin"].choices = location_choices
        self.fields["locatie_einde"].choices = location_choices

        self.fields["categories"].choices = [
            (str(item["code"]), item["name"])
            for item in service.get_category_choices()
        ]

        self.fields["variants"].choices = [
            (str(item["id"]), item["name"])
            for item in service.get_variant_choices()
        ]

        functional_names = {
            "expliciet",
            "verouderd",
            "beledigend",
            "neologisme",
            "negatief",
        }

        labels = service.get_label_choices()

        self.fields["functional_labels"].choices = [
            (str(item["id"]), item["name"])
            for item in labels
            if item["name"].strip().lower() in functional_names
        ]

        self.fields["internal_labels"].choices = [
            (str(item["id"]), item["name"])
            for item in labels
            if item["name"].strip().lower() not in functional_names
        ]

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

    def clean_categories(self):
        categories = self.cleaned_data["categories"]

        if len(categories) > 5:
            raise forms.ValidationError(
                "Je kunt maximaal vijf categorieën toevoegen."
            )

        return categories