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

    // Beschikbaar voor de Signbankmodal
    window.initializeSignbankEditor = initializeSignbankEditor;

    // Initialiseren op gewone detailpagina
    document.addEventListener("DOMContentLoaded", function () {
        initializeSignbankEditor(document);
    });
})();