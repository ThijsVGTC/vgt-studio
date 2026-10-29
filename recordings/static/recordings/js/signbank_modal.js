// Centrale opslagfunctie voor Signbankformulieren in de modal
document.addEventListener("submit", async function (event) {
    const form = event.target;
    const modal = document.getElementById("signbank-edit-modal");

    if (!modal || modal.hidden || !modal.contains(form)) {
        return;
    }

    event.preventDefault();

    if (form.dataset.submitting === "true") {
        return;
    }

    form.dataset.submitting = "true";

    const submitButton = event.submitter;

    if (submitButton) {
        submitButton.disabled = true;
    }

    try {
        const formData = new FormData(form);

        if (submitButton?.name) {
            formData.append(submitButton.name, submitButton.value);
        }

        // Respecteer de specifieke actie van de aangeklikte knop.
        const action = submitButton?.hasAttribute("formaction")
            ? submitButton.formAction
            : form.action;

        const method = submitButton?.hasAttribute("formmethod")
            ? submitButton.formMethod
            : (form.method || "POST");

        const response = await fetch(action, {
            method: method.toUpperCase(),
            body: formData,
            credentials: "same-origin",
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const contentType = response.headers.get("content-type") || "";

        if (!contentType.includes("application/json")) {
            throw new Error("De server gaf geen JSON-antwoord terug.");
        }

        const result = await response.json();

        if (!result.success) {
            const errorMessage = result.messages
                ?.map(item => item.message)
                .join("\n");

            alert(errorMessage || "Opslaan is niet gelukt.");
            return;
        }

        // Onthoud dat de Signbankgegevens gewijzigd zijn.
        modal.dataset.hasChanges = "true";

        // Actuele Signbankgegevens opnieuw laden.
        await openSignbankEditModal(modal.dataset.signbankId);

    } catch (error) {
        console.error("Signbank opslaan mislukt:", error);

        alert(
            "Er is een fout opgetreden bij het opslaan. " +
            "Controleer de gegevens voordat je opnieuw probeert."
        );

    } finally {
        form.dataset.submitting = "false";

        if (submitButton) {
            submitButton.disabled = false;
        }
    }
}, true);

async function openSignbankEditModal(signbankId) {
    const modal = document.getElementById("signbank-edit-modal");
    const title = document.getElementById("signbank-edit-title");
    const content = document.getElementById("signbank-edit-content");

    if (!modal || !content || !signbankId) return;

    title.textContent = "Signbankgegevens bewerken";
    content.textContent = "Signbankgegevens laden...";

    modal.hidden = false;
    modal.classList.add("is-open");
    modal.dataset.signbankId = signbankId;

    modal.querySelector(".signbank-modal-close")?.focus();

    try {
        const url = `/signbank/${encodeURIComponent(signbankId)}/?modal=1`;

        const response = await fetch(url, {
            credentials: "same-origin"
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const html = await response.text();

        // Voorkom dat een oud verzoek een andere entry overschrijft.
        if (
            modal.hidden ||
            modal.dataset.signbankId !== String(signbankId)
        ) {
            return;
        }

        content.innerHTML = html;
        // Activeer de interactieve Signbankvelden
        if (typeof window.initializeSignbankEditor === "function") {
            window.initializeSignbankEditor(content);
        }

    } catch (error) {
        console.error("Signbank laden mislukt:", error);

        if (
            !modal.hidden &&
            modal.dataset.signbankId === String(signbankId)
        ) {
            content.textContent =
                "De Signbankgegevens konden niet worden geladen.";
        }
    }
}

async function refreshSignbankListRow(signbankId) {
    const row = document.querySelector(
        `tr[data-signbank-id="${CSS.escape(String(signbankId))}"]`
    );

    if (!row) return;

    try {
        // Neem de actieve zoekopdracht en filters over.
        const params = new URLSearchParams(window.location.search);

        const response = await fetch(
            `/signbank/${encodeURIComponent(signbankId)}/row/?${params.toString()}`,
            {
                credentials: "same-origin"
            }
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        // De gewijzigde rij voldoet niet meer aan de actieve filters.
        if (response.status === 204) {
            row.remove();
            return;
        }

        const html = await response.text();

        const template = document.createElement("template");
        template.innerHTML = html.trim();

        const newRow = template.content.querySelector("tr");

        if (!newRow) {
            throw new Error("Geen geldige tabelrij ontvangen.");
        }

        row.replaceWith(newRow);

    } catch (error) {
        console.error("Signbankrij bijwerken mislukt:", error);
    }
}

async function closeSignbankEditModal() {
    const modal = document.getElementById("signbank-edit-modal");

    if (!modal) return;

    const signbankId = modal.dataset.signbankId;
    const hasChanges = modal.dataset.hasChanges === "true";

    modal.classList.remove("is-open");
    modal.hidden = true;

    delete modal.dataset.signbankId;
    delete modal.dataset.hasChanges;

    if (!hasChanges || !signbankId) return;

    // Signbank-lijst: vernieuw de gewijzigde rij.
    const signbankRow = document.querySelector(
        `tr[data-signbank-id="${CSS.escape(signbankId)}"]`
    );

    if (signbankRow) {
        await refreshSignbankListRow(signbankId);
        return;
    }

    // Andere pagina's: meld dat Signbankgegevens gewijzigd zijn.
    document.dispatchEvent(
        new CustomEvent("signbank:updated", {
            detail: { signbankId }
        })
    );
}

document.addEventListener("DOMContentLoaded", function () {
    const modal = document.getElementById("signbank-edit-modal");

    if (!modal) return;

    modal.querySelector(".signbank-modal-close")
        ?.addEventListener("click", closeSignbankEditModal);

    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            closeSignbankEditModal();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !modal.hidden) {
            closeSignbankEditModal();
        }
    });
});
