from zoneinfo import ZoneInfo

from django.utils import timezone


def _insert(conn, table, values):
    """
    Alleen aanroepen met vaste tabel- en kolomnamen uit deze module.
    Alle ingevulde waarden worden als SQL-parameters doorgegeven.
    """
    columns = ", ".join(f'"{name}"' for name in values)
    placeholders = ", ".join("?" for _ in values)

    cursor = conn.execute(
        f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})',
        tuple(values.values()),
    )

    return cursor.lastrowid


def _keyword_id(conn, text):
    row = conn.execute(
        "SELECT id FROM dictionary_keyword WHERE text = ?",
        (text,),
    ).fetchone()

    if row:
        return row["id"]

    return _insert(
        conn,
        "dictionary_keyword",
        {"text": text},
    )


def insert_signbank_entry(conn, data, signbank_user_id):
    """
    Maak een gebaar aan met gevalideerde formuliergegevens.

    De aanroepende functie moet de transactie starten en afronden.
    Deze functie doet zelf geen commit en geen synchronisatie.
    """
    gloss = data["gloss"].strip()

    if not gloss or len(gloss) > 30:
        raise ValueError("De GLOSS moet 1 tot 30 tekens bevatten.")

    if gloss in {".", ".."} or any(
        character in gloss for character in ("/", "\\", "\x00")
    ):
        raise ValueError("De GLOSS bevat ongeldige tekens.")

    for field in (
        "handvorm_begin",
        "handvorm_einde",
        "locatie_begin",
        "locatie_einde",
    ):
        if not data.get(field) or str(data[field]) == "0":
            raise ValueError("Handvormen en locaties zijn verplicht.")

    if not data.get("translations"):
        raise ValueError("Voeg minstens één mogelijke vertaling toe.")

    categories = data.get("categories", [])

    if not 1 <= len(categories) <= 5:
        raise ValueError("Kies minstens één en maximaal vijf categorieën.")

    if len(categories) != len(set(categories)):
        raise ValueError("Een categorie mag maar één keer voorkomen.")

    user = conn.execute(
        """
        SELECT id, username, is_active
        FROM auth_user
        WHERE id = ?
        """,
        (signbank_user_id,),
    ).fetchone()

    if user is None or not user["is_active"]:
        raise ValueError("Geen actieve Signbank-gebruiker gevonden.")

    if data.get("comments") and user["username"].lower() in {"ety", "oldety"}:
        raise ValueError(
            "Deze gebruikersnaam is gereserveerd voor etymologie."
        )

    existing = conn.execute(
        """
        SELECT id
        FROM dictionary_gloss
        WHERE annotation_idgloss = ? COLLATE NOCASE
           OR idgloss = ? COLLATE NOCASE
        LIMIT 1
        """,
        (gloss, gloss),
    ).fetchone()

    if existing:
        raise ValueError(f"De GLOSS '{gloss}' bestaat al in Signbank.")

    languages = conn.execute(
        """
        SELECT id
        FROM dictionary_signlanguage
        WHERE LOWER(TRIM(name)) IN ('vgt', 'vlaamse gebarentaal')
        """
    ).fetchall()

    if len(languages) != 1:
        raise ValueError(
            "De taal Vlaamse Gebarentaal kon niet eenduidig "
            "worden gevonden in Signbank."
        )

    # De bestaande Studio-koppeling gebruikt taal-ID 2
    # voor Nederlandse vertalingen.
    translation_language = conn.execute(
        "SELECT id FROM dictionary_language WHERE id = 2"
    ).fetchone()

    if translation_language is None:
        raise ValueError("De vertaaltaal ontbreekt in Signbank.")

    choices_to_check = [
        ("Handshape", data["handvorm_begin"]),
        ("Handshape", data["handvorm_einde"]),
        ("Location", data["locatie_begin"]),
        ("Location", data["locatie_einde"]),
    ] + [
        ("SemField", code) for code in categories
    ]

    for field, code in choices_to_check:
        choice = conn.execute(
            """
            SELECT id
            FROM dictionary_fieldchoice
            WHERE field = ?
              AND CAST(machine_value AS TEXT) = ?
            LIMIT 1
            """,
            (field, str(code)),
        ).fetchone()

        if choice is None:
            raise ValueError(
                "Een gekozen handvorm, locatie of categorie "
                "is niet meer beschikbaar."
            )

    now = timezone.localtime(
        timezone.now(),
        timezone=ZoneInfo("Europe/Brussels"),
    )

    # Deze tekstvelden hebben in het Signbank-model
    # geen NULL-waarde en krijgen bij een nieuw gebaar een lege tekst.
    values = dict.fromkeys(
        [
            "useInstr",
            "rmrks",
            "compound",
            "inittext",
            "morph",
            "mouthG",
            "mouthing",
            "phonetVar",
            "iconImg",
            "derivHist",
        ],
        "",
    )

    values.update({
        "idgloss": gloss,
        "annotation_idgloss": gloss,
        "subhndsh": data["handvorm_begin"],
        "final_subhndsh": data["handvorm_einde"],
        "locprim": data["locatie_begin"],
        "final_loc": int(data["locatie_einde"]),
        "inWeb": int(data["in_woordenboek"]),
        "isNew": 1,
        "repeat": 0,
        "altern": 0,
        "creationDate": now.date().isoformat(),
        "lastUpdated": now.strftime("%Y-%m-%d %H:%M:%S.%f"),
    })

    category_columns = (
        "semField",
        "semField1",
        "semField2",
        "semField3",
        "semField4",
    )

    category_values = categories + [None] * (5 - len(categories))
    values.update(zip(category_columns, category_values))

    signbank_id = _insert(conn, "dictionary_gloss", values)

    _insert(conn, "dictionary_gloss_signlanguage", {
        "gloss_id": signbank_id,
        "signlanguage_id": languages[0]["id"],
    })

    for table in (
        "dictionary_gloss_creator",
        "dictionary_gloss_lastUpdater",
    ):
        _insert(conn, table, {
            "gloss_id": signbank_id,
            "user_id": signbank_user_id,
        })

    for index, text in enumerate(data["translations"]):
        _insert(conn, "dictionary_translation", {
            "gloss_id": signbank_id,
            "translation_id": _keyword_id(conn, text),
            "language_id": 2,
            "index": index,
        })

    for index, text in enumerate(data.get("sources", [])):
        _insert(conn, "dictionary_source", {
            "gloss_id": signbank_id,
            "source_id": _keyword_id(conn, text),
            "index": index,
        })

    for variant_id in dict.fromkeys(data.get("variants", [])):
        variant = conn.execute(
            "SELECT id FROM dictionary_dialect WHERE id = ?",
            (variant_id,),
        ).fetchone()

        if variant is None:
            raise ValueError("Een gekozen variant bestaat niet meer.")

        _insert(conn, "dictionary_gloss_dialect", {
            "gloss_id": signbank_id,
            "dialect_id": variant_id,
        })

    label_ids = set(
        data.get("functional_labels", [])
        + data.get("internal_labels", [])
    )

    if label_ids:
        content_type = conn.execute(
            """
            SELECT id
            FROM django_content_type
            WHERE app_label = 'dictionary' AND model = 'gloss'
            """
        ).fetchone()

        if content_type is None:
            raise ValueError("Het contenttype voor gebaren ontbreekt.")

        for label_id in label_ids:
            label = conn.execute(
                "SELECT id FROM tagging_tag WHERE id = ?",
                (label_id,),
            ).fetchone()

            if label is None:
                raise ValueError("Een gekozen label bestaat niet meer.")

            _insert(conn, "tagging_taggeditem", {
                "tag_id": label_id,
                "content_type_id": content_type["id"],
                "object_id": signbank_id,
            })

    for index, text in enumerate(data.get("comments", [])):
        _insert(conn, "dictionary_definition", {
            "gloss_id": signbank_id,
            "role": user["username"],
            "text": text,
            "count": index,
            "published": 0,
        })

    if data.get("etymology"):
        _insert(conn, "dictionary_definition", {
            "gloss_id": signbank_id,
            "role": "ety",
            "text": data["etymology"],
            "count": 0,
            "published": 0,
        })

    return signbank_id