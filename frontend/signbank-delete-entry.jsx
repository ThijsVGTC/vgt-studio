import React, { useRef, useState } from "react";
import {
    Alert,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Stack,
    TextField,
    Typography,
} from "@mui/material";

export function SignbankDeleteEntry({ url, csrfToken, disabled }) {
    const [open, setOpen] = useState(false);
    const [data, setData] = useState(null);
    const [confirmation, setConfirmation] = useState("");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const busyNow = useRef(false);

    async function openConfirmation() {
        if (busyNow.current || disabled || !url) return;

        busyNow.current = true;
        setBusy(true);
        setOpen(true);
        setData(null);
        setConfirmation("");
        setError("");

        try {
            const response = await fetch(url, {
                credentials: "same-origin",
                cache: "no-store",
                headers: { Accept: "application/json" },
                signal: AbortSignal.timeout(20000),
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                setError(
                    result.error ||
                    "De verwijdergegevens konden niet worden geladen."
                );
                return;
            }

            if (!result.entry || !result.confirmationToken) {
                throw new Error("Onvolledig antwoord.");
            }

            setData(result);
        } catch {
            setError(
                "De verwijdergegevens konden niet worden geladen. " +
                "Sluit dit venster en probeer opnieuw."
            );
        } finally {
            busyNow.current = false;
            setBusy(false);
        }
    }

    async function submit(event) {
        event.preventDefault();

        if (
            busyNow.current ||
            !data?.canSubmit ||
            confirmation !== data.entry.gloss
        ) {
            return;
        }

        busyNow.current = true;
        setBusy(true);
        setError("");

        let navigating = false;

        try {
            const payload = new URLSearchParams();
            payload.set("confirmation_token", data.confirmationToken);
            payload.set("confirm_gloss", confirmation);

            const response = await fetch(url, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: payload,
                signal: AbortSignal.timeout(90000),
            });

            const result = await response.json();

            if (
                response.ok &&
                result.success === true &&
                result.deleted === true &&
                typeof result.redirectUrl === "string"
            ) {
                const target = new URL(
                    result.redirectUrl,
                    window.location.origin
                );

                if (target.origin !== window.location.origin) {
                    throw new Error("Ongeldige terugkeerlocatie.");
                }

                window.location.assign(target.href);
                navigating = true;
                return;
            }

            if (result.success === false) {
                setData((current) => ({
                    ...current,
                    ...result,
                    canSubmit: result.canSubmit === true,
                }));
                setError(
                    result.error || "Verwijderen is niet gelukt."
                );
                return;
            }

            throw new Error("Geen eenduidige bevestiging.");
        } catch {
            setData((current) => ({
                ...current,
                canSubmit: false,
            }));
            setError(
                "Geen bevestiging ontvangen. Controleer eerst in " +
                "Signbank of de entry nog bestaat voordat je opnieuw probeert."
            );
        } finally {
            if (!navigating) {
                busyNow.current = false;
                setBusy(false);
            }
        }
    }

    function close() {
        if (!busyNow.current) setOpen(false);
    }

    return (
        <>
            <Button
                color="error"
                variant="outlined"
                disabled={disabled || busy || !url}
                onClick={openConfirmation}
                sx={{ textTransform: "none" }}
            >
                Signbank-entry verwijderen
            </Button>

            <Dialog
                open={open}
                onClose={close}
                disableEscapeKeyDown={busy}
                fullWidth
                maxWidth="sm"
                className="vgt-signbank-create-dialog"
                aria-labelledby="signbank-delete-entry-title"
            >
                <DialogTitle id="signbank-delete-entry-title">
                    Signbank-entry verwijderen?
                </DialogTitle>

                <DialogContent dividers>
                    <Stack
                        component="form"
                        id="signbank-delete-entry-form"
                        spacing={2}
                        onSubmit={submit}
                    >
                        {busy && (
                            <Typography role="status">
                                {data
                                    ? "Bezig met verwijderen…"
                                    : "Gegevens laden…"}
                            </Typography>
                        )}

                        {error && (
                            <Alert severity="error">{error}</Alert>
                        )}

                        {data?.entry && (
                            <>
                                <Typography>
                                    <strong>{data.entry.gloss}</strong>
                                    {" · "}Signbank-ID {data.entry.id}
                                </Typography>

                                <Typography>
                                    Je verwijdert deze entry definitief uit
                                    Signbank, inclusief de gekoppelde gegevens
                                    die Signbank bij een verwijdering opruimt.
                                    Deze actie kun je hier niet ongedaan maken.
                                </Typography>

                                <Typography>
                                    Bestaande opnames en Gebarometerresultaten
                                    in Studio blijven bewaard.
                                </Typography>

                                <Typography>
                                    Typ <strong>{data.entry.gloss}</strong>
                                    {" "}om de verwijdering te bevestigen.
                                </Typography>

                                <TextField
                                    autoFocus
                                    fullWidth
                                    required
                                    label="GLOSS ter bevestiging"
                                    value={confirmation}
                                    disabled={busy || !data.canSubmit}
                                    onChange={(event) =>
                                        setConfirmation(event.target.value)
                                    }
                                    autoComplete="off"
                                    slotProps={{
                                        htmlInput: { spellCheck: false },
                                    }}
                                />
                            </>
                        )}
                    </Stack>
                </DialogContent>

                <DialogActions>
                    <Button disabled={busy} onClick={close}>
                        Annuleren
                    </Button>

                    <Button
                        type="submit"
                        form="signbank-delete-entry-form"
                        color="error"
                        variant="contained"
                        disableElevation
                        disabled={
                            busy ||
                            !data?.canSubmit ||
                            confirmation !== data?.entry?.gloss
                        }
                    >
                        Definitief verwijderen
                    </Button>
                </DialogActions>
            </Dialog>
        </>
    );
}