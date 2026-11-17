(() => {
    const state = window.signbankCreate;
    if (!state) return;

    const get = (name) =>
        document.getElementById(`signbank-create-${name}`);

    const modal = get("modal");
    const form = get("form");

    const makeRow = (list, field, label, focusTarget) => {
        const row = document.createElement("div");

        row.style.cssText =
            "display:flex; align-items:flex-start; gap:10px; margin-bottom:8px;";

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "button-secondary";
        remove.textContent = "✕";
        remove.setAttribute("aria-label", `${label} verwijderen`);

        remove.addEventListener("click", () => {
            row.remove();
            state.showError();
            focusTarget.focus();
        });

        row.append(field, remove);
        list.append(row);

        return row;
    };

    const bindChoiceList = ({
        selectId,
        listId,
        buttonId,
        name,
        label,
        maximum = Infinity,
    }) => {
        const select = get(selectId);
        const list = get(listId);

        get(buttonId).addEventListener("click", () => {
            const value = select.value;

            if (!value) {
                state.showError(`Selecteer eerst een ${label}.`);
                select.focus();
                return;
            }

            const fields = [...list.querySelectorAll("input")];

            if (fields.some(field => field.value === value)) {
                state.showError("Deze keuze staat al in de lijst.");
                return;
            }

            if (fields.length >= maximum) {
                state.showError(
                    `Je kunt maximaal ${maximum} ${listId} toevoegen.`
                );
                return;
            }

            const text =
                select.options[select.selectedIndex].textContent.trim();

            const field = document.createElement("input");
            field.type = "hidden";
            field.name = name;
            field.value = value;

            const row = makeRow(list, field, label, select);

            const caption = document.createElement("span");
            caption.textContent = text;
            caption.style.flex = "1";

            row.prepend(caption);

            select.value = "";
            state.showError();
            select.focus();
        });
    };

    bindChoiceList({
        selectId: "category",
        listId: "categories",
        buttonId: "add-category",
        name: "categories",
        label: "categorie",
        maximum: 5,
    });

    bindChoiceList({
        selectId: "variant",
        listId: "variants",
        buttonId: "add-variant",
        name: "variants",
        label: "variant",
    });

    bindChoiceList({
        selectId: "internal-label",
        listId: "internal-labels",
        buttonId: "add-internal-label",
        name: "internal_labels",
        label: "intern label",
    });

    const bindTextList = ({
        inputId,
        listId,
        buttonId,
        name,
        label,
        multiline = false,
    }) => {
        const input = get(inputId);
        const list = get(listId);

        const add = () => {
            const text = input.value.trim();

            if (!text) {
                state.showError(`Vul eerst een ${label} in.`);
                input.focus();
                return;
            }

            const existing = [...list.querySelectorAll("input, textarea")];

            if (existing.some(
                field =>
                    field.value.trim().toLowerCase() === text.toLowerCase()
            )) {
                state.showError("Deze tekst staat al in de lijst.");
                return;
            }

            const field = document.createElement(
                multiline ? "textarea" : "input"
            );

            if (multiline) {
                field.rows = 3;
            } else {
                field.type = "text";
                field.maxLength = 100;
            }

            field.name = name;
            field.value = text;
            field.required = true;
            field.setAttribute("aria-label", label);
            field.style.cssText =
                "flex:1; min-width:0; width:auto; box-sizing:border-box;";

            makeRow(list, field, label, input);

            input.value = "";
            state.showError();
            input.focus();
        };

        get(buttonId).addEventListener("click", add);

        if (!multiline) {
            input.addEventListener("keydown", (event) => {
                if (event.key === "Enter") {
                    event.preventDefault();
                    add();
                }
            });
        }
    };

    bindTextList({
        inputId: "comment",
        listId: "comments",
        buttonId: "add-comment",
        name: "comments",
        label: "opmerking",
        multiline: true,
    });

    bindTextList({
        inputId: "source",
        listId: "sources",
        buttonId: "add-source",
        name: "sources",
        label: "bron",
    });

    const closeHandshapeMenus = () => {
        modal.querySelectorAll(".handshape-picker-options").forEach(menu => {
            menu.hidden = true;
        });

        modal.querySelectorAll("[data-create-handshape-toggle]").forEach(
            button => button.setAttribute("aria-expanded", "false")
        );
    };

    modal.addEventListener("click", (event) => {
        const toggle = event.target.closest("[data-create-handshape-toggle]");

        if (toggle) {
            const picker = toggle.closest(".handshape-picker");
            const menu = picker.querySelector(".handshape-picker-options");
            const shouldOpen = menu.hidden;

            closeHandshapeMenus();

            menu.hidden = !shouldOpen;
            toggle.setAttribute("aria-expanded", String(shouldOpen));
            return;
        }

        const option = event.target.closest("[data-create-handshape-option]");

        if (option) {
            const picker = option.closest(".handshape-picker");
            const button = picker.querySelector("[data-create-handshape-toggle]");

            picker.querySelector("input").value = option.dataset.code;

            if (option.dataset.code) {
                button.replaceChildren(
                    ...[...option.childNodes].map(node => node.cloneNode(true))
                );
            } else {
                button.textContent = "Kies handvorm";
            }

            closeHandshapeMenus();
            button.focus();
            return;
        }

        closeHandshapeMenus();
    });

    form.addEventListener("reset", () => {
        modal.querySelectorAll("[data-create-list]").forEach(list => {
            list.replaceChildren();
        });

        modal.querySelectorAll(".handshape-picker").forEach(picker => {
            picker.querySelector("input").value = "";

            picker.querySelector(
                "[data-create-handshape-toggle]"
            ).textContent = "Kies handvorm";
        });

        closeHandshapeMenus();
    });
})();