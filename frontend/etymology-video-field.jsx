import React, { useEffect, useRef, useState } from "react";
import { Box, Stack, TextField } from "@mui/material";

function getVimeoEmbedUrl(value) {
    try {
        const url = new URL(value.trim());

        if (
            !["http:", "https:"].includes(url.protocol) ||
            ![
                "vimeo.com",
                "www.vimeo.com",
                "player.vimeo.com",
            ].includes(url.hostname)
        ) {
            return null;
        }

        const match = url.pathname.match(
            /^\/(?:video\/)?(\d+)(?:\/([a-zA-Z0-9]+))?\/?$/
        );

        if (!match) return null;

        const embed = new URL(
            `https://player.vimeo.com/video/${match[1]}`
        );

        const privacyHash = url.searchParams.get("h") || match[2];

        if (privacyHash) {
            embed.searchParams.set("h", privacyHash);
        }

        return embed.href;
    } catch {
        return null;
    }
}

export function EtymologyVideoField({
    defaultValue = "",
    ...props
}) {
    const [previewValue, setPreviewValue] = useState(defaultValue);
    const input = useRef(null);
    const embedUrl = getVimeoEmbedUrl(previewValue);

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