(function () {
    "use strict";

    function initializeSignbankEditor(container) {
        const categories = container.querySelector("#selected-categories");
        const select = container.querySelector("#category-select");
        const addButton = container.querySelector("#add-category");

        if (!categories || !select || !addButton) return;

        // Voorkom dubbele eventlisteners
        if (categories.dataset.initialized === "true") return;
        categories.dataset.initialized = "true";

        function updateState() {
            const count = categories.querySelectorAll(".selected-category").length;
            addButton.disabled = count >= 5;
        }

        addButton.addEventListener("click", function () {
            const id = select.value;

            if (!id) return;

            if (categories.querySelector(`[data-id="${id}"]`)) {
                alert("Deze categorie is al toegevoegd.");
                return;
            }

            if (categories.querySelectorAll(".selected-category").length >= 5) {
                alert("Je kunt maximaal vijf categorieën toevoegen.");
                return;
            }

            const name = select.options[select.selectedIndex].text;

            const item = document.createElement("div");
            item.className = "selected-category";
            item.dataset.id = id;
            item.style.cssText =
                "display:flex;gap:10px;align-items:center;margin-bottom:8px;";

            const label = document.createElement("span");
            label.textContent = name;

            const hidden = document.createElement("input");
            hidden.type = "hidden";
            hidden.name = "categories";
            hidden.value = id;

            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "remove-category btn btn-sm btn-outline-danger";
            remove.textContent = "✕";

            item.append(label, hidden, remove);
            categories.appendChild(item);

            select.value = "";
            updateState();
        });

        categories.addEventListener("click", function (event) {
            const button = event.target.closest(".remove-category");
            if (!button) return;

            button.closest(".selected-category").remove();
            updateState();
        });

        updateState();
    }

    function initializeSignbankVariants(container) {
        const variants = container.querySelector("#selected-variants");
        const select = container.querySelector("#variant-select");
        const addButton = container.querySelector("#add-variant");

        if (!variants || !select || !addButton) return;

        if (variants.dataset.initialized === "true") return;
        variants.dataset.initialized = "true";

        addButton.addEventListener("click", function () {
            const id = select.value;
            if (!id) return;

            const exists = Array.from(
                variants.querySelectorAll(".selected-variant")
            ).some(item => item.dataset.id === id);

            if (exists) {
                alert("Deze variant is al toegevoegd.");
                return;
            }

            const name = select.options[select.selectedIndex].text;

            const item = document.createElement("div");
            item.className = "selected-variant";
            item.dataset.id = id;
            item.style.cssText =
                "display:flex;gap:10px;align-items:center;margin-bottom:8px;";

            const label = document.createElement("span");
            label.textContent = name;

            const hidden = document.createElement("input");
            hidden.type = "hidden";
            hidden.name = "variants";
            hidden.value = id;

            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "remove-variant btn btn-sm btn-outline-danger";
            remove.textContent = "✕";
            remove.setAttribute(
                "aria-label",
                `Variant ${name} verwijderen`
            );

            item.append(label, hidden, remove);
            variants.appendChild(item);

            select.value = "";
        });

        variants.addEventListener("click", function (event) {
            const button = event.target.closest(".remove-variant");
            if (!button) return;

            button.closest(".selected-variant")?.remove();
        });
    }

    function initializeSignbankLabels(container) {
        const labels = container.querySelector("#selected-labels");
        const select = container.querySelector("#label-select");
        const addButton = container.querySelector("#add-label");

        if (!labels || !select || !addButton) return;

        // Voorkom dubbele eventlisteners
        if (labels.dataset.initialized === "true") return;
        labels.dataset.initialized = "true";

        addButton.addEventListener("click", function () {
            const id = select.value;
            if (!id) return;

            const exists = Array.from(
                labels.querySelectorAll(".selected-label")
            ).some(item => item.dataset.id === id);

            if (exists) {
                alert("Dit label is al toegevoegd.");
                return;
            }

            const name = select.options[select.selectedIndex].text;

            const item = document.createElement("div");
            item.className = "selected-label";
            item.dataset.id = id;
            item.style.cssText =
                "display:flex;gap:10px;align-items:center;margin-bottom:8px;";

            const label = document.createElement("span");
            label.textContent = name;

            const hidden = document.createElement("input");
            hidden.type = "hidden";
            hidden.name = "labels";
            hidden.value = id;

            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "remove-label btn btn-sm btn-outline-danger";
            remove.textContent = "✕";
            remove.setAttribute(
                "aria-label",
                `Label ${name} verwijderen`
            );

            item.append(label, hidden, remove);
            labels.appendChild(item);

            select.value = "";
        });

        labels.addEventListener("click", function (event) {
            const button = event.target.closest(".remove-label");
            if (!button) return;

            button.closest(".selected-label")?.remove();
        });
    }

    // Beschikbaar voor de Signbankmodal
    const initializeCategories = initializeSignbankEditor;

    window.initializeSignbankEditor = function (container) {
        initializeCategories(container);
        initializeSignbankVariants(container);
        initializeSignbankLabels(container);
    };

    // Initialiseren op gewone detailpagina
    document.addEventListener("DOMContentLoaded", function () {
        initializeSignbankEditor(document);
    });
})();