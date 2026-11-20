import React, { useEffect, useRef, useState } from "react";
import { Alert, Button, Paper, Stack, Typography } from "@mui/material";
import { EtymologyPairForm } from "./etymology-pair-form.jsx";
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

export function EtymologyPairs({
  url,
  disabled = false,
  onBusyChange,
  onChanged,
}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [notice, setNotice] = useState(null);
  const [activePair, setActivePair] = useState(undefined);
  const savingNow = useRef(false);

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
async function savePair(payload) {
  if (!data || disabled || blocked || savingNow.current) return;

  savingNow.current = true;
  setSaving(true);
  setNotice(null);
  onBusyChange?.(true);

  try {
    const response = await fetch(data.saveUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "X-CSRFToken": data.csrfToken,
      },
      body: payload,
      signal: AbortSignal.timeout(180000),
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      if (result.outcomeUnknown !== false) {
        throw new Error("Opslag niet bevestigd.");
      }

      const messages = Object.values(result.errors || {})
        .flat()
        .map((item) => item.message)
        .filter(Boolean);

      setNotice({
        severity: "error",
        text: messages.join(" ") || result.error || "Opslaan mislukt.",
      });
      return;
    }

    if (!result.pair || !Number.isInteger(result.pair.pairNumber)) {
      throw new Error("Onvolledige opslagbevestiging.");
    }

    setData((current) => ({
      ...current,
      pairs: [
        ...current.pairs.filter(
          (pair) => pair.pairNumber !== result.pair.pairNumber
        ),
        result.pair,
      ].sort((a, b) => a.pairNumber - b.pairNumber),
    }));

    setActivePair(undefined);
    onChanged?.();

    setNotice({
      severity: result.warning ? "warning" : "success",
      text: result.warning || "Etymologiepaar opgeslagen.",
    });
  } catch {
    setBlocked(true);
    setNotice({
      severity: "error",
      text: "Geen opslagbevestiging ontvangen. Heropen dit scherm om te controleren of het paar is opgeslagen.",
    });
  } finally {
    savingNow.current = false;
    setSaving(false);
    onBusyChange?.(false);
  }
}
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!data) return <Typography>Etymologie laden…</Typography>;

  return (
    <Stack spacing={2}>
        {notice && (
        <Alert severity={notice.severity}>{notice.text}</Alert>
        )}
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
            {data.canEdit && !pair.ambiguous && (
            <Button
                variant="outlined"
                disabled={
                disabled || saving || blocked || activePair !== undefined
                }
                onClick={() => setActivePair(pair)}
                sx={{ alignSelf: "flex-end" }}
            >
                Paar bewerken
            </Button>
            )}
          </Stack>
        </Paper>
      ))}
      {data.canEdit && activePair !== undefined && (
  <Paper variant="outlined" sx={{ p: 2 }}>
    <EtymologyPairForm
      key={activePair ? activePair.pairNumber : "new"}
      pair={activePair}
      config={data}
      disabled={disabled || saving || blocked}
      onSave={savePair}
      onCancel={() => setActivePair(undefined)}
    />
  </Paper>
)}

{data.canEdit && activePair === undefined && (
  <Button
    variant="contained"
    disabled={disabled || saving || blocked}
    onClick={() => setActivePair(null)}
    sx={{ alignSelf: "flex-start" }}
  >
    Etymologiepaar toevoegen
  </Button>
)}
    </Stack>
  );
}