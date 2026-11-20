import React, { useEffect, useRef, useState } from "react";
import { Alert, Box, Button, Stack, Typography } from "@mui/material";

export function EtymologyCamera({
    onRecorded,
    onCancel,
    disabled = false,
}) {
    const video = useRef(null);
    const stream = useRef(null);
    const recorder = useRef(null);
    const chunks = useRef([]);
    const timer = useRef(null);
    const active = useRef(false);

    const [attempt, setAttempt] = useState(0);
    const [opening, setOpening] = useState(true);
    const [ready, setReady] = useState(false);
    const [recording, setRecording] = useState(false);
    const [seconds, setSeconds] = useState(0);
    const [error, setError] = useState("");

    function stopResources() {
        window.clearInterval(timer.current);

        if (recorder.current) {
            recorder.current.ondataavailable = null;
            recorder.current.onstop = null;
            recorder.current.onerror = null;

            if (recorder.current.state !== "inactive") {
                try {
                    recorder.current.stop();
                } catch {
                    // De opname kan al gestopt zijn.
                }
            }

            recorder.current = null;
        }

        stream.current?.getTracks().forEach((track) => track.stop());
        stream.current = null;
    }

    useEffect(() => {
        let cancelled = false;
        active.current = true;

        setOpening(true);
        setReady(false);
        setError("");

        async function openCamera() {
            try {
                if (
                    !navigator.mediaDevices?.getUserMedia ||
                    typeof MediaRecorder === "undefined"
                ) {
                    throw new Error(
                        "Deze browser ondersteunt webcamopnames niet."
                    );
                }

                const media = await navigator.mediaDevices.getUserMedia({
                    audio: false,
                    video: {
                        width: { ideal: 1280 },
                        height: { ideal: 720 },
                        aspectRatio: { ideal: 16 / 9 },
                        frameRate: { ideal: 30 },
                    },
                });

                if (cancelled) {
                    media.getTracks().forEach((track) => track.stop());
                    return;
                }

                stream.current = media;

                if (video.current) {
                    video.current.srcObject = media;
                    await video.current.play();
                }

                if (!cancelled) setReady(true);
            } catch (failure) {
                if (!cancelled) {
                    setError(
                        failure.name === "NotAllowedError"
                            ? "Geef toestemming om de camera te gebruiken."
                            : failure.message || "De camera kon niet openen."
                    );
                    stopResources();
                }
            } finally {
                if (!cancelled) setOpening(false);
            }
        }

        openCamera();

        return () => {
            cancelled = true;
            active.current = false;
            stopResources();
        };
    }, [attempt]);

    function startRecording() {
        if (!ready || recording || disabled || !stream.current) return;

        setError("");
        setSeconds(0);
        chunks.current = [];

        try {
            const mimeType = [
                "video/webm;codecs=vp9",
                "video/webm;codecs=vp8",
                "video/mp4",
                "video/webm",
            ].find((type) => MediaRecorder.isTypeSupported(type));

            const options = {
                videoBitsPerSecond: 2500000,
                ...(mimeType ? { mimeType } : {}),
            };

            const capture = new MediaRecorder(stream.current, options);
            recorder.current = capture;

            capture.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    chunks.current.push(event.data);
                }
            };

            capture.onstop = () => {
                window.clearInterval(timer.current);

                if (!active.current) return;

                const type = (
                    capture.mimeType ||
                    chunks.current[0]?.type ||
                    "video/webm"
                );

                const blob = new Blob(chunks.current, { type });
                const extension = type.includes("mp4") ? "mp4" : "webm";

                stopResources();
                setRecording(false);
                setReady(false);

                if (!blob.size) {
                    setError("De opname is leeg. Probeer opnieuw.");
                    return;
                }

                onRecorded(
                    new File(
                        [blob],
                        `etymology-recording.${extension}`,
                        { type }
                    )
                );
            };

            capture.onerror = () => {
                stopResources();

                if (active.current) {
                    setRecording(false);
                    setReady(false);
                    setError(
                        "De opname is mislukt. Open de camera opnieuw."
                    );
                }
            };

            capture.start(500);
            setRecording(true);

            timer.current = window.setInterval(
                () => setSeconds((value) => value + 1),
                1000
            );
        } catch {
            setError("De opname kon niet starten.");
        }
    }

    function stopRecording() {
        if (recorder.current?.state === "recording") {
            recorder.current.stop();
        }
    }

    const duration = (
        `${Math.floor(seconds / 60).toString().padStart(2, "0")}:` +
        `${(seconds % 60).toString().padStart(2, "0")}`
    );

    return (
        <Stack spacing={1}>
            {opening && (
                <Typography role="status">Camera openen…</Typography>
            )}

            {error && <Alert severity="error">{error}</Alert>}

            <Box
                component="video"
                ref={video}
                autoPlay
                muted
                playsInline
                sx={{
                    display: ready || recording ? "block" : "none",
                    width: "100%",
                    maxHeight: 360,
                    bgcolor: "#000",
                    borderRadius: 2,
                }}
            />

            {recording && (
                <Typography role="status">
                    Opname bezig · {duration}
                </Typography>
            )}

            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                {ready && !recording && (
                    <Button
                        variant="contained"
                        disabled={disabled}
                        onClick={startRecording}
                        sx={{
                        bgcolor: "primary.main",
                        color: "primary.contrastText",
                        textTransform: "none",
                        fontWeight: 700,
                        "&:hover": {
                            bgcolor: "primary.dark",
                        },
                        }}
                    >
                        Opname starten
                    </Button>
                )}

                {recording && (
                    <Button
                        variant="contained"
                        color="error"
                        onClick={stopRecording}
                    >
                        Opname stoppen
                    </Button>
                )}

                {!opening && !ready && !recording && (
                    <Button
                        variant="outlined"
                        disabled={disabled}
                        onClick={() => setAttempt((value) => value + 1)}
                    >
                        Camera opnieuw openen
                    </Button>
                )}

                <Button
                    variant="outlined"
                    disabled={disabled}
                    onClick={onCancel}
                >
                    Annuleren
                </Button>
            </Stack>
        </Stack>
    );
}