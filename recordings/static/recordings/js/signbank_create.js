(() => {
    const modal = document.getElementById("signbank-create-modal");
    if (!modal) return;

    const get = (name) =>
        document.getElementById(`signbank-create-${name}`);

    const form = get("form");
    const input = get("video");
    const preview = get("preview");
    const details = get("details");
    const next = get("continue");

    const state = {
        video: null,
        previewUrl: null,
        saving: false,
        stopCamera: () => {},
    };

    window.signbankCreate = state;

    state.showError = (message = "") => {
        get("error").textContent = message;
        get("error").hidden = !message;
    };

    state.showChoice = () => {
        state.stopCamera();
        preview.pause();
        preview.removeAttribute("src");
        preview.load();

        if (state.previewUrl) {
            URL.revokeObjectURL(state.previewUrl);
            state.previewUrl = null;
        }

        state.video = null;
        input.value = "";

        get("choice").hidden = false;
        get("camera").hidden = true;
        get("review").hidden = true;
        details.hidden = true;
        details.disabled = true;
        get("save").disabled = true;
        get("status").textContent = "";

        state.showError();
    };

    state.showVideo = (file) => {
        if (!file || file.size === 0) {
            state.showError("De video is leeg. Kies een andere video.");
            return;
        }

        state.showChoice();
        state.video = file;
        state.previewUrl = URL.createObjectURL(file);

        next.disabled = true;
        preview.src = state.previewUrl;
        preview.load();

        get("choice").hidden = true;
        get("review").hidden = false;
        get("status").textContent = file.name;
    };

    preview.addEventListener("loadedmetadata", () => {
        next.disabled = preview.videoWidth === 0;

        if (next.disabled) {
            state.showError("Dit bestand bevat geen afspeelbaar videobeeld.");
        }
    });

    preview.addEventListener("error", () => {
        if (!state.video) return;

        next.disabled = true;
        state.showError(
            "Deze browser kan de video niet afspelen. Kies een andere video."
        );
    });

    get("upload").addEventListener("click", () => {
        input.value = "";
        input.click();
    });

    input.addEventListener("change", () => {
        const file = input.files[0];
        if (file) state.showVideo(file);
    });

    next.addEventListener("click", () => {
        if (!state.video || next.disabled) return;

        preview.pause();
        details.hidden = false;
        details.disabled = false;
        get("gloss").focus();
    });

    get("retry").addEventListener("click", state.showChoice);

    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-signbank-create]");

        if (button && !modal.open) {
            event.preventDefault();
            modal.showModal();
        }
    });

    const close = () => {
        if (state.saving) return;

        const hasInput =
            state.video ||
            !get("camera").hidden ||
            get("gloss").value.trim() ||
            get("translation").value.trim();

        if (hasInput && !window.confirm(
            "Venster sluiten en de niet-opgeslagen invoer wissen?"
        )) return;

        state.showChoice();
        form.reset();
        get("translations").replaceChildren();
        modal.close();
    };

    get("close").addEventListener("click", close);

    modal.addEventListener("cancel", (event) => {
        if (event.target === input) return;

        event.preventDefault();
        close();
    });
    const translations = get("translations");
    const translationInput = get("translation");

    const addTranslation = () => {
        const text = translationInput.value.trim();

        if (!text) {
            state.showError("Vul eerst een mogelijke vertaling in.");
            translationInput.focus();
            return;
        }

        const existing = [...translations.querySelectorAll("input")];

        if (existing.some(
            input => input.value.trim().toLowerCase() === text.toLowerCase()
        )) {
            state.showError("Deze vertaling staat al in de lijst.");
            translationInput.focus();
            return;
        }

        const row = document.createElement("div");
        row.className = "translation-item";
        row.style.cssText =
            "display:flex; align-items:center; gap:10px; margin-bottom:8px;";

        const field = document.createElement("input");
        field.type = "text";
        field.name = "translations";
        field.value = text;
        field.maxLength = 100;
        field.required = true;
        field.setAttribute("aria-label", "Mogelijke vertaling");
        field.style.cssText = "flex:1; min-width:0; width:auto;";

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "button-secondary";
        remove.textContent = "✕";
        remove.title = "Vertaling verwijderen";
        remove.setAttribute("aria-label", "Vertaling verwijderen");

        remove.addEventListener("click", () => {
            row.remove();
            translationInput.focus();
        });

        row.append(field, remove);
        translations.append(row);

        translationInput.value = "";
        state.showError();
        translationInput.focus();
    };

    get("add-translation").addEventListener("click", addTranslation);

    translationInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            addTranslation();
        }
    });
    // De opslag koppelen we in een volgende stap.
    form.addEventListener("submit", (event) => {
        event.preventDefault();
    });
})();