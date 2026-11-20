import React, { useEffect, useRef, useState } from "react";
import { Box, Stack, TextField, Typography } from "@mui/material";

export function EtymologyVideoField({
    defaultValue = "",
    resolveUrl,
    ...props
}) {
    const [previewValue, setPreviewValue] = useState(defaultValue);
    const [embedUrl, setEmbedUrl] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const input = useRef(null);

    useEffect(() => {
        const form = input.current?.form;

        function resetPreview() {
            setPreviewValue(defaultValue);
        }

        form?.addEventListener("reset", resetPreview);

        return () => {
            form?.removeEventListener("reset", resetPreview);
        };
    }, [defaultValue]);

    useEffect(() => {
        const originalUrl = previewValue.trim();

        setEmbedUrl("");
        setError("");
        setLoading(false);

        if (!originalUrl) return;

        if (!resolveUrl) {
            setError(
                "Het videovoorbeeld is nog niet beschikbaar. " +
                "Vernieuw de pagina."
            );
            return;
        }

        const controller = new AbortController();
        let active = true;
        let timeout;

        const delay = window.setTimeout(async () => {
            setLoading(true);

            timeout = window.setTimeout(
                () => controller.abort(),
                25000
            );

            try {
                const target = new URL(
                    resolveUrl,
                    window.location.origin
                );
                target.searchParams.set("url", originalUrl);

                const response = await fetch(target.href, {
                    credentials: "same-origin",
                    headers: { Accept: "application/json" },
                    signal: controller.signal,
                });

                const result = await response.json();

                if (!active) return;

                if (
                    !response.ok ||
                    result.success !== true ||
                    typeof result.embedUrl !== "string"
                ) {
                    throw new Error(
                        result.error ||
                        "Het videovoorbeeld kon niet worden opgehaald."
                    );
                }

                const player = new URL(result.embedUrl);

                if (
                    player.origin !== "https://player.vimeo.com" ||
                    !/^\/video\/[0-9]+$/.test(player.pathname)
                ) {
                    throw new Error(
                        "Vimeo gaf geen geldige spelerlink terug."
                    );
                }

                setEmbedUrl(player.href);
            } catch (failure) {
                if (active) {
                    setError(
                        failure.name === "AbortError"
                            ? "Vimeo reageert niet op tijd. Probeer opnieuw."
                            : failure instanceof SyntaxError
                                ? "Het videovoorbeeld kon niet worden opgehaald."
                                : failure.message ||
                                  "Het videovoorbeeld kon niet worden opgehaald."
                    );
                }
            } finally {
                window.clearTimeout(timeout);
                if (active) setLoading(false);
            }
        }, 400);

        return () => {
            active = false;
            window.clearTimeout(delay);
            window.clearTimeout(timeout);
            controller.abort();
        };
    }, [previewValue, resolveUrl]);

    return (
        <Stack spacing={1}>
            <TextField
                {...props}
                defaultValue={defaultValue}
                inputRef={input}
                onChange={(event) =>
                    setPreviewValue(event.target.value)
                }
            />

            {loading && (
                <Typography variant="body2" role="status">
                    Videovoorbeeld laden…
                </Typography>
            )}

            {error && (
                <Typography
                    variant="body2"
                    color="error"
                    role="alert"
                >
                    {error}
                </Typography>
            )}

            {embedUrl && (
                <Box
                    sx={{
                        width: "100%",
                        maxWidth: 640,
                        aspectRatio: "16 / 9",
                        position: "relative",
                        overflow: "hidden",
                        borderRadius: 2,
                        bgcolor: "#000",
                    }}
                >
                    <Box
                        component="iframe"
                        key={embedUrl}
                        src={embedUrl}
                        title="Etymologievideo"
                        loading="lazy"
                        allow="fullscreen; picture-in-picture"
                        allowFullScreen
                        sx={{
                            position: "absolute",
                            inset: 0,
                            width: "100%",
                            height: "100%",
                            border: 0,
                        }}
                    />
                </Box>
            )}
        </Stack>
    );
}