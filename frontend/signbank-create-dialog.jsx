import React, { useCallback, useEffect, useRef, useState } from "react";
import {
    Alert, Autocomplete, Box, Button, Chip, Dialog, DialogActions,
    DialogContent, DialogTitle, IconButton, MenuItem, Stack,
    TextField, Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

const cameraConstraints = {
    audio: false,
    video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        aspectRatio: { ideal: 16 / 9 },
        frameRate: { ideal: 30 },
        resizeMode: { ideal: "none" },
    },
};

const videoTypes = [
    "video/webm;codecs=vp9",
    "video/webm;codecs=vp8",
    "video/mp4",
    "video/webm",
];

const listFields = [
    "translations", "categories", "variants", "functional_labels",
    "internal_labels", "comments", "sources",
];

const fieldLabels = {
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

function cameraTime(seconds) {
    const pad = (value) => String(value).padStart(2, "0");
    return `${pad(Math.floor(seconds / 60))}:${pad(seconds % 60)}`;
}

function CreateSignDialog({ mount, options, highContrast, onClose }) {
    const [step, setStep] = useState("choice");
    const [file, setFile] = useState(null);
    const [previewUrl, setPreviewUrl] = useState("");
    const [canPlay, setCanPlay] = useState(false);
    const [cameraStatus, setCameraStatus] = useState("opening");
    const [cameraRatio, setCameraRatio] = useState(16 / 9);
    const [seconds, setSeconds] = useState(0);
    const [values, setValues] = useState({ in_woordenboek: "0" });
    const [error, setError] = useState("");
    const [saving, setSaving] = useState(false);
    const [retryBlocked, setRetryBlocked] = useState(false);
    const [saved, setSaved] = useState(null);
    const [confirmClose, setConfirmClose] = useState(false);

    const live = useRef(null);
    const upload = useRef(null);
    const stream = useRef(null);
    const recorder = useRef(null);
    const automaticStart = useRef(false);
    const source = useRef("");
    const submitInProgress = useRef(false);

    const setField = (name, value) => {
        setValues((previous) => ({ ...previous, [name]: value }));
    };

    const showVideo = useCallback((videoFile, videoSource) => {
        if (!videoFile?.size) {
            setError("De video is leeg. Probeer opnieuw.");
            setStep("choice");
            return;
        }

        source.current = videoSource;
        setCanPlay(false);
        setError("");
        setFile(videoFile);
        setStep("review");
    }, []);

    const startRecording = useCallback(() => {
        if (!stream.current || recorder.current) return;

        try {
            const mimeType = videoTypes.find(
                (type) => window.MediaRecorder.isTypeSupported?.(type)
            );
            const settings = { videoBitsPerSecond: 2500000 };
            if (mimeType) settings.mimeType = mimeType;

            const activeRecorder = new window.MediaRecorder(stream.current, settings);
            const chunks = [];

            activeRecorder.ondataavailable = ({ data }) => {
                if (data.size) chunks.push(data);
            };

            activeRecorder.onstop = () => {
                if (recorder.current !== activeRecorder) return;

                const type = activeRecorder.mimeType || chunks[0]?.type || "video/webm";
                const extension = type.includes("mp4") ? "mp4" : "webm";
                showVideo(new File(chunks, `webcamopname.${extension}`, { type }), "webcam");
            };

            activeRecorder.onerror = () => {
                setError("De opname is mislukt. Probeer opnieuw of upload een video.");
                setStep("choice");
            };

            recorder.current = activeRecorder;
            activeRecorder.start(250);
            setSeconds(0);
            setCameraStatus("recording");
        } catch {
            setError("De opname kon niet starten. Probeer opnieuw of upload een video.");
            setStep("choice");
        }
    }, [showVideo]);

    useEffect(() => {
        if (step !== "camera") return;

        let closed = false;
        const video = live.current;
        const startImmediately = automaticStart.current;
        automaticStart.current = false;

        function releaseCamera() {
            closed = true;
            const activeRecorder = recorder.current;
            recorder.current = null;

            if (activeRecorder) {
                activeRecorder.ondataavailable = null;
                activeRecorder.onstop = null;
                activeRecorder.onerror = null;

                if (activeRecorder.state !== "inactive") activeRecorder.stop();
            }

            stream.current?.getTracks().forEach((track) => track.stop());
            stream.current = null;
            video.srcObject = null;
        }

        async function openCamera() {
            if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
                setError("Webcamopname is niet beschikbaar in deze browser. Open Studio via HTTPS of upload een video.");
                setStep("choice");
                return;
            }

            try {
                const camera = await navigator.mediaDevices.getUserMedia(cameraConstraints);

                if (closed) {
                    camera.getTracks().forEach((track) => track.stop());
                    return;
                }

                stream.current = camera;
                video.srcObject = camera;
                await video.play();

                if (closed) return;

                setCameraStatus("ready");
                if (startImmediately) startRecording();
            } catch (cameraError) {
                if (closed) return;

                setError(cameraError.name === "NotAllowedError"
                    ? "Geef Studio toestemming om je webcam te gebruiken."
                    : "De webcam kon niet worden geopend. Controleer of een andere app ze gebruikt.");
                setStep("choice");
            }
        }

        window.addEventListener("pagehide", releaseCamera);
        openCamera();

        return () => {
            window.removeEventListener("pagehide", releaseCamera);
            releaseCamera();
        };
    }, [step, startRecording]);

    useEffect(() => {
        if (cameraStatus !== "recording" || step !== "camera") return;
        const startedAt = Date.now();
        const timer = window.setInterval(() => {
            setSeconds(Math.floor((Date.now() - startedAt) / 1000));
        }, 250);
        return () => window.clearInterval(timer);
    }, [cameraStatus, step]);

    useEffect(() => {
        if (!file) {
            setPreviewUrl("");
            return;
        }

        const url = URL.createObjectURL(file);
        setPreviewUrl(url);
        return () => URL.revokeObjectURL(url);
    }, [file]);

    useEffect(() => {
        if ((!file && step !== "camera") || saved) return;

        function warnBeforeLeaving(event) {
            event.preventDefault();
            event.returnValue = "";
        }

        window.addEventListener("beforeunload", warnBeforeLeaving);
        return () => window.removeEventListener("beforeunload", warnBeforeLeaving);
    }, [file, step, saved]);

    useEffect(() => {
        if (saved && !saved.warnings?.length) {
            window.location.assign(saved.redirect_url);
        }
    }, [saved]);

    function openCamera(recordImmediately = false) {
        automaticStart.current = recordImmediately;
        setCanPlay(false);
        setFile(null);
        setError("");
        setSeconds(0);
        setCameraRatio(16 / 9);
        setCameraStatus("opening");
        setStep("camera");
    }

    function stopRecording() {
        if (recorder.current?.state !== "recording") return;
        setCameraStatus("finishing");
        recorder.current.stop();
    }

    function goToChoice() {
        setFile(null);
        setCanPlay(false);
        setError("");
        setStep("choice");
    }

    function requestClose() {
        if (submitInProgress.current) return;

        if (!saved && (file || step === "camera" || Object.keys(values).length > 1)) {
            setConfirmClose(true);
        } else {
            onClose();
        }
    }

    async function save(event) {
        event.preventDefault();
        if (submitInProgress.current || retryBlocked || saved || !file || !canPlay) return;

        if (!values.translations?.length || !values.categories?.length) {
            setError("Voeg minstens één vertaling en één categorie toe.");
            return;
        }

        if (values.categories.length > 5) {
            setError("Je kunt maximaal vijf categorieën toevoegen.");
            return;
        }

        const payload = new FormData();
        payload.set("csrfmiddlewaretoken", mount.dataset.csrfToken);
        payload.set("video", file, file.name);

        for (const [name, value] of Object.entries(values)) {
            if (listFields.includes(name)) {
                for (const item of value) {
                    payload.append(name, typeof item === "string" ? item : item.value);
                }
            } else {
                payload.set(name, value);
            }
        }

        submitInProgress.current = true;
        setSaving(true);
        setError("");

        try {
            const response = await fetch(mount.dataset.createUrl, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: payload,
            });

            if (!response.headers.get("content-type")?.includes("application/json")) {
                setRetryBlocked(true);
                setError(response.redirected || response.status === 403
                    ? "Je sessie is mogelijk verlopen. Je video en gegevens blijven in dit venster beschikbaar."
                    : "Er kwam geen bruikbare bevestiging. Controleer eerst of het gebaar al in Signbank staat.");
                return;
            }

            const result = await response.json();
            if (!response.ok || !result.ok) {
                setRetryBlocked(result.retry_allowed === false);
                const messages = Object.entries(result.errors || {}).flatMap(
                    ([field, errors]) => errors.map(
                        (message) => `${fieldLabels[field] || field}: ${message}`
                    )
                );
                setError([result.error || "Opslaan is mislukt.", ...messages].join("\n"));
                return;
            }

            setSaved(result);
        } catch {
            setRetryBlocked(true);
            setError("Er kwam geen bevestiging. Controleer eerst of het gebaar al in Signbank staat. Je invoer blijft hier beschikbaar.");
        } finally {
            submitInProgress.current = false;
            setSaving(false);
        }
    }

    function choices(key, idKey) {
        return (options[key] ?? []).map((item) => ({
            value: String(item[idKey]),
            label: item.name,
        }));
    }

    function selectField(name, label, items, withImages = false) {
        return (
            <TextField
                select required fullWidth size="small" label={label}
                value={values[name] ?? ""}
                onChange={(event) => setField(name, event.target.value)}
            >
                {items.filter(({ value }) => value && value !== "0").map(({ value, label: text }) => (
                    <MenuItem key={value} value={value}>
                        {withImages && (
                            <Box component="img"
                                 src={`${mount.dataset.handshapeBase}handshape_${encodeURIComponent(value)}.png`}
                                 alt="" loading="lazy"
                                 sx={{ width: 34, height: 34, objectFit: "contain", mr: 1 }} />
                        )}
                        {text}
                    </MenuItem>
                ))}
            </TextField>
        );
    }

    function multiField(name, label, items = null) {
        const freeText = items === null;

        return (
            <Autocomplete
                multiple
                freeSolo={freeText}
                autoSelect={freeText}
                size="small"
                options={items ?? []}
                value={values[name] ?? []}
                filterSelectedOptions
                getOptionLabel={(item) => typeof item === "string" ? item : item.label}
                isOptionEqualToValue={(item, value) =>
                    typeof item === "string" || typeof value === "string"
                        ? item === value
                        : item.value === value.value
                }
                onChange={(_, selection) => setField(name, freeText
                    ? [...new Set(selection.map((item) => item.trim()).filter(Boolean))]
                    : selection
                )}
                renderInput={(params) => (
                    <TextField
                        {...params}
                        label={label}
                        helperText={freeText ? "Druk op Enter om toe te voegen." : undefined}
                    />
                )}
            />
        );
    }

    const shapes = choices("handshape_choices", "code");
    const locations = choices("location_choices", "code");
    const isRecording = cameraStatus === "recording";
    const isFinishing = cameraStatus === "finishing";

    const filled = (background, color, hover) => ({
        bgcolor: highContrast ? "#FFE500" : background,
        color: highContrast ? "#000" : color,
        textTransform: "none",
        "&:hover": { bgcolor: highContrast ? "#FFF36A" : hover },
    });

    const blue = filled("#6075A6", "#fff", "#566B9B");
    const coral = filled("#F3705D", "#261511", "#FF8978");

    return (
        <>
            <Dialog
                open onClose={requestClose} fullWidth
                maxWidth={step === "details" ? "md" : "sm"}
                aria-labelledby="react-signbank-create-title"
                scroll="paper" disableEscapeKeyDown={saving}
            >
                <DialogTitle id="react-signbank-create-title" sx={{ pr: 7 }}>
                    Nieuw gebaar toevoegen
                    <IconButton aria-label="Venster sluiten" onClick={requestClose}
                                disabled={saving} sx={{ position: "absolute", right: 12, top: 12 }}>
                        <CloseIcon />
                    </IconButton>
                </DialogTitle>

                <DialogContent dividers>
                    <Stack spacing={2}>
                        {error && <Alert severity="error" sx={{ whiteSpace: "pre-line" }}>{error}</Alert>}

                        {saved ? (
                            <Alert severity={saved.warnings?.length ? "warning" : "success"}>
                                Gebaar {saved.signbank_id} en de video zijn opgeslagen.
                                {saved.warnings?.map((warning) => <div key={warning}>{warning}</div>)}
                            </Alert>
                        ) : step === "choice" ? (
                            <>
                                <Typography>Kies hoe je de video toevoegt.</Typography>
                                <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                                    <Button autoFocus variant="contained" disableElevation
                                            sx={blue} onClick={() => openCamera()}>
                                        Webcamopname maken
                                    </Button>
                                    <Button variant="outlined" sx={{ textTransform: "none" }}
                                            onClick={() => upload.current.click()}>
                                        Video uploaden
                                    </Button>
                                </Stack>
                                <input ref={upload} type="file" accept="video/*" hidden
                                       onChange={(event) => {
                                           const selected = event.target.files[0];
                                           event.target.value = "";
                                           if (selected) showVideo(selected, "upload");
                                       }} />
                            </>
                        ) : step === "camera" ? (
                            <>
                                <Typography role="status">
                                    {cameraStatus === "opening" ? "Webcam openen…" :
                                     isFinishing ? "Opname wordt voorbereid…" :
                                     isRecording ? "Opname loopt…" :
                                     "Zorg dat je handen en gezicht volledig in beeld zijn."}
                                </Typography>
                                <Box sx={{
                                    position: "relative", alignSelf: "center", overflow: "hidden",
                                    width: `min(100%, ${46 * cameraRatio}dvh)`,
                                    aspectRatio: String(cameraRatio), borderRadius: 2, bgcolor: "#111",
                                }}>
                                    <Box component="video" ref={live} autoPlay muted playsInline
                                         onResize={(event) => {
                                             const { videoWidth, videoHeight } = event.currentTarget;
                                             if (videoWidth && videoHeight) {
                                                 setCameraRatio(videoWidth / videoHeight);
                                             }
                                         }}
                                         sx={{ display: "block", width: "100%", height: "100%", objectFit: "contain" }} />
                                    <Chip label={cameraTime(seconds)} size="small" aria-hidden="true"
                                          sx={{
                                              position: "absolute", right: 12, bottom: 12,
                                              bgcolor: isRecording ? "#B42318" : "#313F69", color: "#fff",
                                          }} />
                                </Box>
                            </>
                        ) : step === "review" ? (
                            <>
                                <Typography>Bekijk de video voor je verdergaat.</Typography>
                                {previewUrl && (
                                    <Box component="video" key={previewUrl} src={previewUrl}
                                         controls playsInline preload="metadata"
                                         onLoadedMetadata={(event) => {
                                             const playable = event.currentTarget.videoWidth > 0;
                                             setCanPlay(playable);
                                             if (!playable) setError("Dit bestand bevat geen afspeelbaar videobeeld.");
                                         }}
                                         onError={() => {
                                             setCanPlay(false);
                                             setError("Deze browser kan de video niet afspelen. Kies een andere video.");
                                         }}
                                         sx={{
                                             display: "block", maxWidth: "100%", maxHeight: "46dvh",
                                             alignSelf: "center", borderRadius: 2, objectFit: "contain",
                                         }} />
                                )}
                            </>
                        ) : (
                            <Box component="form" id="react-signbank-create-form" onSubmit={save}>
                                <Box component="fieldset" disabled={saving}
                                     sx={{
                                         m: 0, p: 0, border: 0, minWidth: 0,
                                         display: "grid", gap: 1.5,
                                         gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
                                     }}>
                                    <TextField autoFocus required size="small" label="GLOSS"
                                               value={values.gloss ?? ""}
                                               slotProps={{ htmlInput: { maxLength: 30 } }}
                                               onChange={(event) => setField("gloss", event.target.value)} />
                                    <TextField select size="small" label="In woordenboek"
                                               value={values.in_woordenboek}
                                               onChange={(event) => setField("in_woordenboek", event.target.value)}>
                                        <MenuItem value="0">Nee</MenuItem>
                                        <MenuItem value="1">Ja</MenuItem>
                                    </TextField>
                                    <Box sx={{ gridColumn: "1 / -1" }}>
                                        {multiField("translations", "Mogelijke vertalingen")}
                                    </Box>
                                    {selectField("handvorm_begin", "Handvorm begin", shapes, true)}
                                    {selectField("handvorm_einde", "Handvorm einde", shapes, true)}
                                    {selectField("locatie_begin", "Locatie begin", locations)}
                                    {selectField("locatie_einde", "Locatie einde", locations)}
                                    {multiField("categories", "Categorieën", choices("category_choices", "code"))}
                                    {multiField("variants", "Varianten", choices("variant_choices", "id"))}
                                    {multiField("functional_labels", "Functionele labels", choices("functional_label_choices", "id"))}
                                    {multiField("internal_labels", "Interne labels", choices("internal_label_choices", "id"))}
                                    <Box sx={{ gridColumn: "1 / -1" }}>
                                        {multiField("comments", "Opmerkingen Signbank")}
                                    </Box>
                                    <TextField multiline minRows={1} size="small" label="Etymologie"
                                               value={values.etymology ?? ""}
                                               sx={{ gridColumn: "1 / -1" }}
                                               onChange={(event) => setField("etymology", event.target.value)} />
                                    <Box sx={{ gridColumn: "1 / -1" }}>
                                        {multiField("sources", "Bronnen")}
                                    </Box>
                                </Box>
                            </Box>
                        )}
                    </Stack>
                </DialogContent>

                {(saved || step !== "choice") && (
                    <DialogActions sx={{ px: 3, py: 1.5, flexWrap: "wrap" }}>
                        {saved ? (
                            <Button href={saved.redirect_url} variant="contained" sx={blue}>
                                Naar het gebaar
                            </Button>
                        ) : step === "camera" ? (
                            <>
                                <Button variant="outlined" disabled={isFinishing}
                                        onClick={goToChoice}>Terug</Button>
                                {isRecording || isFinishing ? (
                                    <Button variant="contained" disableElevation sx={coral}
                                            disabled={isFinishing} onClick={stopRecording}>
                                        Opname stoppen
                                    </Button>
                                ) : (
                                    <Button variant="contained" disableElevation sx={coral}
                                            disabled={cameraStatus !== "ready"} onClick={startRecording}>
                                        Opname starten
                                    </Button>
                                )}
                            </>
                        ) : step === "review" ? (
                            <>
                                <Button variant="outlined" onClick={() =>
                                    source.current === "webcam" ? openCamera(true) : goToChoice()
                                }>
                                    {source.current === "webcam" ? "Opnieuw opnemen" : "Andere video kiezen"}
                                </Button>
                                <Button variant="contained" disableElevation sx={blue}
                                        disabled={!canPlay} onClick={() => setStep("details")}>
                                    Gegevens invullen
                                </Button>
                            </>
                        ) : (
                            <>
                                <Button variant="outlined" disabled={saving || retryBlocked}
                                        onClick={() => { setError(""); setStep("review"); }}>
                                    Video bekijken
                                </Button>
                                <Button type="submit" form="react-signbank-create-form"
                                        variant="contained" disableElevation sx={coral}
                                        disabled={saving || retryBlocked}>
                                    {saving ? "Bezig met opslaan…" : "Gebaar en video opslaan"}
                                </Button>
                            </>
                        )}
                    </DialogActions>
                )}
            </Dialog>

            <Dialog open={confirmClose} onClose={() => setConfirmClose(false)}
                    aria-labelledby="react-signbank-discard-title">
                <DialogTitle id="react-signbank-discard-title">Invoer wissen?</DialogTitle>
                <DialogContent>
                    <Typography>Je opname en ingevulde gegevens worden gewist als je het venster sluit.</Typography>
                </DialogContent>
                <DialogActions>
                    <Button autoFocus onClick={() => setConfirmClose(false)}>Verder werken</Button>
                    <Button onClick={onClose}>Sluiten en wissen</Button>
                </DialogActions>
            </Dialog>
        </>
    );
}

export function SignbankCreateDialog({ mount, highContrast }) {
    const [open, setOpen] = useState(false);
    const options = React.useMemo(
        () => JSON.parse(document.getElementById("signbank-create-options").textContent),
        []
    );

    useEffect(() => {
        function openFromButton(event) {
            if (!event.target.closest?.("[data-signbank-create]")) return;
            event.preventDefault();
            setOpen(true);
        }

        document.addEventListener("click", openFromButton);
        return () => document.removeEventListener("click", openFromButton);
    }, []);

    return open ? (
        <CreateSignDialog mount={mount} options={options}
                          highContrast={highContrast} onClose={() => setOpen(false)} />
    ) : null;
}