(() => {
    const state = window.signbankCreate;
    if (!state) return;

    const get = (name) =>
        document.getElementById(`signbank-create-${name}`);

    const form = get("form");
    const details = get("details");
    const save = get("save");

    let blocked = false;
    let completed = false;

    get("error").style.whiteSpace = "pre-line";

    const fail = (message, element) => {
        state.showError(message);
        element?.focus();
        return false;
    };

    const validateDetails = () => {
        state.showError();

        if (!state.video || state.video.size === 0) {
            return fail("Upload een video of maak een webcamopname.");
        }

        if (!get("gloss").value.trim()) {
            return fail("Vul de GLOSS in.", get("gloss"));
        }

        for (const [name, message] of [
            ["handvorm-begin", "Kies een handvorm voor het begin."],
            ["handvorm-einde", "Kies een handvorm voor het einde."],
        ]) {
            const input = get(name);

            if (!input.value || input.value === "0") {
                return fail(
                    message,
                    input.closest(".handshape-picker").querySelector(
                        "[data-create-handshape-toggle]"
                    )
                );
            }
        }

        for (const [name, message] of [
            ["locatie-begin", "Kies een locatie voor het begin."],
            ["locatie-einde", "Kies een locatie voor het einde."],
        ]) {
            if (!get(name).value || get(name).value === "0") {
                return fail(message, get(name));
            }
        }

        // Voorkom dat ingevulde maar nog niet toegevoegde
        // teksten of keuzes ongemerkt verloren gaan.
        for (const [name, message] of [
            [
                "translation",
                "Voeg de ingevulde vertaling eerst toe met '+ Vertaling toevoegen'.",
            ],
            [
                "category",
                "Voeg de geselecteerde categorie eerst toe met '+ Toevoegen'.",
            ],
            [
                "variant",
                "Voeg de geselecteerde variant eerst toe met '+ Toevoegen'.",
            ],
            [
                "internal-label",
                "Voeg het geselecteerde interne label eerst toe met '+ Toevoegen'.",
            ],
            [
                "comment",
                "Voeg de ingevulde opmerking eerst toe met '+ Opmerking toevoegen'.",
            ],
            [
                "source",
                "Voeg de ingevulde bron eerst toe met '+ Bron toevoegen'.",
            ],
        ]) {
            if (get(name).value.trim()) {
                return fail(message, get(name));
            }
        }

        if (!get("translations").querySelector(
            'input[name="translations"]'
        )) {
            return fail(
                "Voeg minstens één mogelijke vertaling toe.",
                get("translation")
            );
        }

        const categories = get("categories").querySelectorAll(
            'input[name="categories"]'
        );

        if (categories.length < 1 || categories.length > 5) {
            return fail(
                "Voeg minstens één en maximaal vijf categorieën toe.",
                get("category")
            );
        }

        return form.reportValidity();
    };

    get("continue").addEventListener("click", () => {
        if (!details.hidden && state.video) {
            save.disabled = blocked || state.saving;
        }
    });

    form.addEventListener("reset", () => {
        blocked = false;
        completed = false;
        save.disabled = true;
        save.textContent = "Gebaar en video opslaan";
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        if (state.saving || blocked || completed || details.hidden) {
            return;
        }

        if (!validateDetails()) return;

        // Verzamel de gegevens voordat we de velden blokkeren.
        const payload = new FormData(form);

        payload.set(
            "video",
            state.video,
            state.video.name || "webcamopname.webm"
        );

        state.saving = true;
        details.disabled = true;
        save.disabled = true;
        get("close").disabled = true;
        get("retry").disabled = true;
        get("continue").disabled = true;

        save.textContent = "Bezig met opslaan…";
        get("status").textContent =
            "De video wordt verwerkt en het gebaar wordt opgeslagen.";

        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: payload,
                credentials: "same-origin",
                headers: {
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            const contentType = response.headers.get("content-type") || "";

            if (!contentType.includes("application/json")) {
                throw new Error(
                    response.redirected || response.status === 403
                        ? "Je sessie is mogelijk verlopen. " +
                          "De video en gegevens blijven in dit venster beschikbaar."
                        : "De server gaf geen bruikbare bevestiging. " +
                          "Controleer of het gebaar al in Signbank staat " +
                          "voordat je opnieuw opslaat."
                );
            }

            const result = await response.json();

            if (!response.ok || !result.ok) {
                blocked = result.retry_allowed === false;

                const messages = [
                    result.error || "Opslaan is mislukt.",
                ];

                const labels = {
                    gloss: "GLOSS",
                    video: "Video",
                    in_woordenboek: "In woordenboek",
                    handvorm_begin: "Handvorm begin",
                    handvorm_einde: "Handvorm einde",
                    locatie_begin: "Locatie begin",
                    locatie_einde: "Locatie einde",
                    translations: "Mogelijke vertalingen",
                    categories: "Categorieën",
                    variants: "Varianten",
                    functional_labels: "Functionele labels",
                    internal_labels: "Interne labels",
                    comments: "Opmerkingen",
                    etymology: "Etymologie",
                    sources: "Bronnen",
                };

                for (const [field, errors] of Object.entries(
                    result.errors || {}
                )) {
                    for (const error of errors) {
                        messages.push(`${labels[field] || field}: ${error}`);
                    }
                }

                state.showError(messages.join("\n"));
                get("status").textContent =
                    "Je video en ingevulde gegevens blijven beschikbaar.";

                return;
            }

            completed = true;
            state.video = null;

            save.textContent = "Opgeslagen";
            get("status").textContent =
                `Gebaar ${result.signbank_id} en de video zijn opgeslagen.`;

            if (result.warnings?.length) {
                window.alert(result.warnings.join("\n\n"));
            }

            window.location.assign(result.redirect_url);

        } catch (error) {
            state.showError(
                error instanceof TypeError
                    ? "Er kwam geen bevestiging van de server. " +
                      "Controleer eerst of het gebaar al is opgeslagen. " +
                      "Je video en gegevens blijven hier beschikbaar."
                    : error.message
            );

            get("status").textContent = "";

        } finally {
            state.saving = false;

            if (!completed) {
                details.disabled = false;
                save.disabled = blocked;
                save.textContent = blocked
                    ? "Controleer eerst de opslaguitkomst"
                    : "Gebaar en video opslaan";

                get("close").disabled = false;
                get("retry").disabled = false;
                get("continue").disabled = false;
            }
        }
    });

    window.addEventListener("beforeunload", (event) => {
        if (!completed && state.video) {
            event.preventDefault();
            event.returnValue = "";
        }
    });
})();