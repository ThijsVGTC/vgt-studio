import React, { useEffect, useState } from "react";
import { Alert, Paper, Stack, Typography } from "@mui/material";
import { EtymologyVideoField } from "./etymology-video-field.jsx";

function EtymologyPlayer({ url, resolveUrl }) {
  let parsed;

  try {
    parsed = new URL(url);
  } catch {
    return <Typography>{url}</Typography>;
  }

  if (
    ["http:", "https:"].includes(parsed.protocol) &&
    ["vimeo.com", "www.vimeo.com", "player.vimeo.com"].includes(parsed.hostname)
  ) {
    return (
      <EtymologyVideoField
        defaultValue={url}
        resolveUrl={resolveUrl}
        label="Etymologievideo"
        type="url"
        fullWidth
        slotProps={{ htmlInput: { readOnly: true } }}
      />
    );
  }

  if (
    parsed.protocol === "https:" &&
    parsed.hostname === "vlaamsegebarentaal.be" &&
    parsed.pathname.startsWith(
      "/signbank/dictionary/protected_media/etymologyvideo/"
    )
  ) {
    return (
      <video
        src={url}
        controls
        playsInline
        preload="metadata"
        style={{ width: "100%", maxHeight: 360, background: "#000" }}
      />
    );
  }

  return <Typography sx={{ overflowWrap: "anywhere" }}>{url}</Typography>;
}

export function EtymologyPairs({ url }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    setData(null);
    setError("");

    async function load() {
      try {
        const response = await fetch(url, {
          credentials: "same-origin",
          cache: "no-store",
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
          throw new Error(result.error || "Etymologie ophalen mislukt.");
        }

        setData(result);
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err.message);
        }
      }
    }

    load();
    return () => controller.abort();
  }, [url]);

  if (error) return <Alert severity="error">{error}</Alert>;
  if (!data) return <Typography>Etymologie laden…</Typography>;

  return (
    <Stack spacing={2}>
      {data.pairs.length === 0 && (
        <Typography>Nog geen etymologie toegevoegd.</Typography>
      )}

      {data.pairs.map((pair) => (
        <Paper key={pair.pairNumber} variant="outlined" sx={{ p: 2 }}>
          <Stack spacing={1}>
            <Typography fontWeight={700}>
              Etymologie {pair.pairNumber}
            </Typography>

            {pair.ambiguous && (
              <Alert severity="warning">
                Bij dit nummer staan meerdere notities. De koppeling moet
                eerst worden nagekeken.
              </Alert>
            )}

            {pair.videos.map((video) => (
                <EtymologyPlayer
                    key={`${video.id}-${video.text}`}
                    url={video.text}
                    resolveUrl={data.vimeoPreviewUrl}
                />
            ))}

            {pair.texts.map((text) => (
              <Typography key={text.id} sx={{ whiteSpace: "pre-wrap" }}>
                {text.text}
              </Typography>
            ))}
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}