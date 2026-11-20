import React, { useCallback, useEffect, useRef, useState } from "react";
import {
    Alert, Autocomplete, Box, Button, Dialog, DialogActions, DialogContent,
    DialogTitle, IconButton, MenuItem, Stack, TextField, Typography, Paper,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { SignbankDeleteEntry } from "./signbank-delete-entry.jsx";

const saveStyle = {
    bgcolor: "var(--create-heading)",
    color: "#fff",
    "&:hover": { bgcolor: "#253153" },
    'html[data-reading-mode="true"] &': {
        bgcolor: "#ffe500",
        color: "#000",
        "&:hover": { bgcolor: "#fff36a" },
    },
};

const detailDateFormat = new Intl.DateTimeFormat("nl-BE", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Brussels",
});

function formatDetailDate(value) {
    return value ? detailDateFormat.format(new Date(value)) : "–";
}

function Section({ title, children, wide = false }) {
    return (
        <Box component="section" sx={{
            minWidth: 0,
            gridColumn: wide ? "1 / -1" : "auto",
            borderTop: "1px solid var(--create-border)",
            pt: 1,
        }}>
            <Typography component="h3" variant="subtitle2"
                        sx={{ fontWeight: 700, mb: 0.75 }}>
                {title}
            </Typography>
            <Stack spacing={1}>{children}</Stack>
        </Box>
    );
}

function EditForm({ url, save, disabled, children, add = false, onDelete }) {
    async function submit(event) {
        event.preventDefault();

        const form = event.currentTarget;
        const successful = await save(url, new FormData(form));
        if (successful && add) form.reset();
    }

    return (
        <Stack component="form" spacing={0.75} onSubmit={submit}>
            {children}
            <Stack direction="row" spacing={0.75} sx={{ justifyContent: "flex-end" }}>
                {onDelete && (
                    <Button size="small" variant="outlined" disabled={disabled}
                            onClick={onDelete}>
                        Verwijderen
                    </Button>
                )}
                <Button type="submit" size="small" variant="contained"
                        disableElevation disabled={disabled || !url} sx={saveStyle}>
                    {add ? "Toevoegen" : "Opslaan"}
                </Button>
            </Stack>
        </Stack>
    );
}

function SelectField({ name, label, initial, options, disabled, emptyLabel }) {
    const [value, setValue] = useState(initial);
    const menuOptions = emptyLabel
        ? [{ value: "0", label: emptyLabel }, ...options]
        : options;

    return (
        <TextField select size="small" fullWidth name={name} label={label}
                   disabled={disabled} value={value}
                   onChange={(event) => setValue(event.target.value)}>
            {!menuOptions.some((item) => item.value === value) && (
                <MenuItem value={value}>{value}</MenuItem>
            )}
            {menuOptions.map((item) => (
                <MenuItem key={item.value} value={item.value}>
                    {item.imageUrl && (
                        <Box component="img" src={item.imageUrl} alt="" loading="lazy"
                             sx={{ width: 32, height: 32, objectFit: "contain", mr: 1 }} />
                    )}
                    {item.label}
                </MenuItem>
            ))}
        </TextField>
    );
}

function MultiField({ name, label, initial, options, disabled, limit }) {
    const [selected, setSelected] = useState(initial);
    const optionByValue = new Map(options.map((item) => [item.value, item]));

    return (
        <>
            <Autocomplete
                multiple size="small" disabled={disabled}
                options={options}
                value={selected.map((value) => optionByValue.get(value) ?? { value, label: value })}
                filterSelectedOptions
                isOptionEqualToValue={(item, value) => item.value === value.value}
                onChange={(_, items) => setSelected(items.map((item) => item.value))}
                getOptionDisabled={(item) =>
                    Boolean(limit && selected.length >= limit && !selected.includes(item.value))
                }
                renderInput={(params) => <TextField {...params} label={label} />}
            />
            {selected.map((value) => (
                <input key={value} type="hidden" name={name} value={value} />
            ))}
        </>
    );
}

function TextItems({
    items,
    addUrl,
    label,
    name,
    save,
    disabled,
    confirmDelete,
    multiline = false,
    type = "text",
    maxLength = 100,
    minRows = 1,
}) {
    const inputOptions = multiline
        ? undefined
        : { htmlInput: { maxLength } };

    return (
        <>
            {items.map((item, index) => (
                item.updateUrl ? (
                    <EditForm
                        key={JSON.stringify([item.id, item.text])}
                        url={item.updateUrl}
                        save={save}
                        disabled={disabled}
                        onDelete={() =>
                            confirmDelete(item.deleteUrl, item.text)
                        }
                    >
                        <TextField
                            name={name}
                            label={item.author || label}
                            defaultValue={item.text}
                            size="small"
                            required
                            disabled={disabled}
                            type={type}
                            multiline={multiline}
                            minRows={multiline ? minRows : undefined}
                            slotProps={inputOptions}
                        />
                    </EditForm>
                ) : (
                    <Typography
                        key={`read-${index}`}
                        variant="body2"
                        sx={{ whiteSpace: "pre-wrap" }}
                    >
                        {item.author && (
                            <strong>{item.author} · </strong>
                        )}
                        {item.text}
                    </Typography>
                )
            ))}

            <EditForm
                url={addUrl}
                save={save}
                disabled={disabled}
                add
            >
                <TextField
                    name={name}
                    label={`${label} toevoegen`}
                    size="small"
                    required
                    disabled={disabled}
                    type={type}
                    multiline={multiline}
                    minRows={multiline ? minRows : undefined}
                    slotProps={inputOptions}
                />
            </EditForm>
        </>
    );
}

export function SignbankEditDialog({ row, onClose, page = false, listUrl }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [refreshFailed, setRefreshFailed] = useState(false);
    const [message, setMessage] = useState(null);
    const [deletion, setDeletion] = useState(null);
    const changed = useRef(false);
    const savingNow = useRef(false);

    const load = useCallback(async (signal) => {
        const url = new URL(row.detailUrl, window.location.origin);
        url.searchParams.set("format", "edit-json");

        const response = await fetch(url, { signal, cache: "no-store" });
        if (!response.ok || !response.headers.get("content-type")?.includes("application/json")) {
            throw new Error("De Signbankgegevens konden niet worden geladen.");
        }

        const result = await response.json();
        if (!signal?.aborted) {
            setData(result);
            setRefreshFailed(false);
        }
    }, [row.detailUrl]);

    useEffect(() => {
        const controller = new AbortController();

        load(controller.signal).catch((error) => {
            if (!controller.signal.aborted) {
                setMessage({ severity: "error", text: error.message });
            }
        }).finally(() => {
            if (!controller.signal.aborted) setLoading(false);
        });

        return () => controller.abort();
    }, [load]);

    async function reload() {
        setLoading(true);
        setMessage(null);

        try {
            await load();
        } catch (error) {
            setMessage({ severity: "error", text: error.message });
        } finally {
            setLoading(false);
        }
    }

    async function save(url, payload) {
        if (!data || savingNow.current || refreshFailed) return false;

        savingNow.current = true;
        setSaving(true);
        setMessage(null);
        payload.set("csrfmiddlewaretoken", data.csrfToken);

        try {
            const response = await fetch(url, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    Accept: "application/json",
                },
                body: payload,
            });

            if (response.status === 403) {
                setMessage({
                    severity: "error",
                    text: "Je hebt geen toestemming voor deze wijziging of je sessie is verlopen.",
                });
                return false;
            }

            if (!response.headers.get("content-type")?.includes("application/json")) {
                throw new Error("Onverwacht antwoord van Signbank.");
            }

            const result = await response.json();
            const text = (result.messages ?? []).map((item) => item.message).join("\n");

            if (!response.ok || !result.success) {
                setMessage({ severity: "error", text: text || "Opslaan is mislukt." });
                return false;
            }

            changed.current = true;
            try {
                await load();
                setMessage({ severity: "success", text: text || "Opgeslagen." });
            } catch {
                setRefreshFailed(true);
                setMessage({
                    severity: "warning",
                    text: "Opgeslagen. Laad de gegevens opnieuw om verder te bewerken.",
                });
            }
            return true;
        } catch {
            changed.current = true;
            setRefreshFailed(true);
            setMessage({
                severity: "warning",
                text: "Geen bevestiging ontvangen. Laad de gegevens opnieuw om te controleren of de wijziging is opgeslagen.",
            });
            return false;
        } finally {
            savingNow.current = false;
            setSaving(false);
        }
    }

    function close() {
        if (savingNow.current) return;
        if (changed.current) {
            window.dispatchEvent(new CustomEvent("signbank:row-updated", {
                detail: { signbankId: row.id },
            }));
        }
        onClose();
    }

    const disabled = loading || saving || refreshFailed;
    const askDelete = (url, text) => setDeletion({ url, text });

    function editChoices(title, url, name, options, initial, extra = {}) {
        return (
            <Section title={title}>
                <EditForm url={url} save={save} disabled={disabled || extra.readOnly}>
                    {extra.type && <input type="hidden" name="label_type" value={extra.type} />}
                    <MultiField key={JSON.stringify(initial)} name={name} label={title}
                                initial={initial} options={options} limit={extra.limit}
                                disabled={disabled || extra.readOnly} />
                </EditForm>
            </Section>
        );
    }

    function editPair(title, url, prefix, options, emptyLabel) {
        return (
            <Section title={title}>
                <EditForm url={url} save={save} disabled={disabled}>
                    <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                        {["begin", "einde"].map((position) => {
                            const name = `${prefix}_${position}`;
                            const initial = data.selected[name];
                            return (
                                <SelectField key={`${name}-${initial}`} name={name}
                                             label={`${title} ${position}`} initial={initial}
                                             options={options} emptyLabel={emptyLabel}
                                             disabled={disabled} />
                            );
                        })}
                    </Stack>
                </EditForm>
            </Section>
        );
    }

    const editorContent = (
                <DialogContent dividers>
                    <Stack spacing={1.5}>
                        {loading && <Typography role="status">Gegevens laden…</Typography>}
                        {saving && <Typography role="status">Bezig met opslaan…</Typography>}
                        {message && (
                            <Alert severity={message.severity} sx={{ whiteSpace: "pre-line" }}>
                                {message.text}
                            </Alert>
                        )}
                        {!loading && (refreshFailed || !data) && (
                            <Button variant="outlined" onClick={reload}
                                    sx={{ alignSelf: "flex-start" }}>
                                Gegevens opnieuw laden
                            </Button>
                        )}

                        {data && (
                            <>
                                {data.videoUrl && (
                                    <Box component="video" key={data.videoUrl} src={data.videoUrl}
                                         controls playsInline preload="metadata"
                                         aria-label={`Video van ${data.gloss}`}
                                         sx={{
                                             display: "block", alignSelf: "center",
                                             maxWidth: "100%", maxHeight: "32dvh",
                                             borderRadius: 2, objectFit: "contain",
                                         }} />
                                )}
                                <Typography variant="body2">Signbank-ID {data.id}</Typography>

                                <Box sx={{
                                    display: "grid", gap: 1.5,
                                    gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
                                }}>
                                    <Section title="GLOSS">
                                        <EditForm url={data.actions.gloss} save={save} disabled={disabled}>
                                            <TextField key={data.gloss} name="new_gloss" label="GLOSS"
                                                       defaultValue={data.gloss} size="small"
                                                       required disabled={disabled} />
                                        </EditForm>
                                    </Section>

                                    <Section title="Woordenboek">
                                        <EditForm url={data.actions.dictionary} save={save} disabled={disabled}>
                                            <SelectField key={data.inDictionary} name="in_woordenboek"
                                                         label="In woordenboek" initial={data.inDictionary}
                                                         options={[
                                                             { value: "0", label: "Nee" },
                                                             { value: "1", label: "Ja" },
                                                         ]}
                                                         disabled={disabled} />
                                        </EditForm>
                                    </Section>

                                    <Section title="Mogelijke vertalingen" wide>
                                        <TextItems items={data.translations} addUrl={data.actions.addTranslation}
                                                   label="Vertaling" name="new_text" save={save}
                                                   disabled={disabled} confirmDelete={askDelete} />
                                    </Section>

                                    {editPair("Handvorm", data.actions.handshapes,
                                              "handvorm", data.handshapes, "Geen handvorm")}
                                    {editPair("Locatie", data.actions.locations,
                                              "locatie", data.locations, "Geen locatie")}
                                    {editChoices("Categorieën", data.actions.categories,
                                                 "categories", data.categories,
                                                 data.selected.categories, { limit: 5 })}
                                    {editChoices("Varianten", data.actions.variants,
                                                 "variants", data.variants, data.selected.variants)}
                                    {editChoices("Functionele labels", data.actions.labels,
                                                 "labels", data.functionalLabels, data.selected.functional,
                                                 { type: "functional", readOnly: !data.canEditLabels })}
                                    {editChoices("Interne labels", data.actions.labels,
                                                 "labels", data.internalLabels, data.selected.internal,
                                                 { type: "internal", readOnly: !data.canEditLabels })}

                                    <Section title="Opmerkingen Signbank" wide>
                                        <TextItems items={data.notes} addUrl={data.actions.addNote}
                                                   label="Opmerking" name="text" save={save}
                                                   disabled={disabled} confirmDelete={askDelete} multiline />
                                    </Section>

                                    {data.otherNotes.length > 0 && (
                                        <Section title="Opmerkingen uit Studio" wide>
                                            {data.otherNotes.map((note, index) => (
                                                <Typography key={index} variant="body2"
                                                            sx={{ whiteSpace: "pre-wrap" }}>
                                                    <strong>
                                                        {[note.source, note.type, note.author]
                                                            .filter(Boolean).join(" · ")}
                                                    </strong>
                                                    <br />
                                                    {note.text}
                                                </Typography>
                                            ))}
                                        </Section>
                                    )}

                                    <Section title="Etymologievideo" wide>
                                        <TextItems
                                            items={data.etymologyVideoItems ?? []}
                                            addUrl={data.actions.addEtymologyVideo}
                                            label="Etymologievideo"
                                            name="text"
                                            type="url"
                                            maxLength={1000}
                                            save={save}
                                            disabled={
                                                disabled ||
                                                !data.canEditEtymology
                                            }
                                            confirmDelete={askDelete}
                                        />
                                    </Section>

                                    <Section title="Etymologietekst" wide>
                                        <TextItems
                                            items={data.etymologyTextItems ?? []}
                                            addUrl={data.actions.addEtymologyText}
                                            label="Etymologietekst"
                                            name="text"
                                            multiline
                                            minRows={4}
                                            save={save}
                                            disabled={
                                                disabled ||
                                                !data.canEditEtymology
                                            }
                                            confirmDelete={askDelete}
                                        />
                                    </Section>

                                    <Section title="Bronnen" wide>
                                        <TextItems items={data.sources} addUrl={data.actions.addSource}
                                                   label="Bron" name="new_text" save={save}
                                                   disabled={disabled} confirmDelete={askDelete} />
                                    </Section>
                                    {page && (
                                        <Typography
                                            variant="body2"
                                            color="text.secondary"
                                            sx={{ gridColumn: "1 / -1" }}
                                        >
                                            Laatste wijziging in Signbank {formatDetailDate(data.lastUpdated)}
                                            {" · "}
                                            Laatst gesynchroniseerd {formatDetailDate(data.syncedAt)}
                                        </Typography>
                                    )}
                                </Box>
                            </>
                        )}
                    </Stack>
                </DialogContent>
            );
        return (
        <>
            {page ? (
                <Stack spacing={2}>
                    <Stack>
                        <Button
                            href={listUrl}
                            variant="text"
                            sx={{ alignSelf: "flex-start", textTransform: "none" }}
                        >
                            ← Terug naar Signbank
                        </Button>
                    </Stack>

                    <Paper
                        component="section"
                        variant="outlined"
                        className="vgt-signbank-create-dialog"
                        aria-labelledby="react-signbank-edit-title"
                        sx={{
                            bgcolor: "var(--create-surface)",
                            color: "var(--create-text)",
                            borderColor: "var(--create-border)",
                            borderRadius: "14px",
                            overflow: "hidden",
                        }}
                    >
                        <DialogTitle component="h1" id="react-signbank-edit-title">
                            {data?.gloss || row.gloss || "Signbank-entry"}
                        </DialogTitle>

                        {page && data?.canDeleteEntry && (
                            <Box sx={{ px: 3, pb: 1.5 }}>
                                <SignbankDeleteEntry
                                    url={data.deleteEntryUrl}
                                    csrfToken={data.csrfToken}
                                    disabled={disabled}
                                />
                            </Box>
                        )}

                        {editorContent}
                    </Paper>
                </Stack>
            ) : (
                <Dialog
                    open
                    onClose={close}
                    className="vgt-signbank-create-dialog"
                    fullWidth
                    maxWidth="md"
                    scroll="paper"
                    aria-labelledby="react-signbank-edit-title"
                >
                    <DialogTitle id="react-signbank-edit-title" sx={{ pr: 7 }}>
                        Signbankgegevens bewerken
                        <IconButton
                            aria-label="Venster sluiten"
                            onClick={close}
                            disabled={saving}
                            sx={{ position: "absolute", right: 12, top: 10 }}
                        >
                            <CloseIcon />
                        </IconButton>
                    </DialogTitle>

                    {editorContent}

                    <DialogActions>
                        <Button variant="outlined" onClick={close} disabled={saving}>
                            Sluiten
                        </Button>
                    </DialogActions>
                </Dialog>
            )}
            {deletion && (
                <Dialog open className="vgt-signbank-create-dialog"
                        onClose={() => { if (!savingNow.current) setDeletion(null); }}
                        aria-labelledby="react-signbank-delete-title">
                    <DialogTitle id="react-signbank-delete-title">Item verwijderen?</DialogTitle>
                    <DialogContent dividers sx={{ overflowWrap: "anywhere" }}>
                        {deletion.text}
                    </DialogContent>
                    <DialogActions>
                        <Button autoFocus disabled={saving} onClick={() => setDeletion(null)}>
                            Annuleren
                        </Button>
                        <Button color="error" disabled={saving}
                                onClick={async () => {
                                    await save(deletion.url, new FormData());
                                    setDeletion(null);
                                }}>
                            Verwijderen
                        </Button>
                    </DialogActions>
                </Dialog>
            )}
        </>
    );
}