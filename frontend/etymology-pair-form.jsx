import React, { useEffect, useState } from "react";
import { EtymologyCamera } from "./etymology-camera.jsx";
import { Alert, Button, MenuItem, Stack, TextField, Checkbox, FormControlLabel } from "@mui/material";
import { EtymologyVideoField } from "./etymology-video-field.jsx";

const primaryButtonSx = {
  backgroundColor: "#303f6b",
  color: "#fff",
  textTransform: "none",
  fontWeight: 700,
  "&:hover": {
    backgroundColor: "#253153",
  },
};

export function EtymologyPairForm({
  pair = null,
  config,
  disabled = false,
  onSave,
  onCancel,
}) {
  const existingVideo = pair?.videos?.[0]?.text || "";
  const [source, setSource] = useState(existingVideo ? "keep" : "vimeo");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [published, setPublished] = useState(pair?.published ?? false);

    useEffect(() => {
    if (!file) {
        setPreviewUrl("");
        return;
    }

    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    return () => URL.revokeObjectURL(url);
    }, [file]);


  function submit(event) {
    event.preventDefault();
    if (disabled) return;

    const payload = new FormData(event.currentTarget);
    payload.set("source_type", source);
    payload.set("published", published ? "true" : "false");
    if (source === "upload" || source === "webcam") {
        if (!file) {
            setError("Kies eerst een videobestand.");
            return;
        }

        payload.set("video", file);
    }

    if (pair) {
      payload.set("pair_number", String(pair.pairNumber));
      payload.set("expected_revision", pair.revision);
    }

    onSave(payload);
  }

  return (
    <Stack component="form" spacing={2} onSubmit={submit}>
      <TextField
        select
        label="Videobron"
        value={source}
        onChange={(event) => {
        setSource(event.target.value);
        setFile(null);
        setError("");
        }}
        disabled={disabled}
      >
        {existingVideo && (
          <MenuItem value="keep">Bestaande video behouden</MenuItem>
        )}
        <MenuItem value="vimeo">Vimeo-link</MenuItem>
        <MenuItem value="upload">Video uploaden</MenuItem>
        <MenuItem value="webcam">Webcamopname</MenuItem>
      </TextField>

      {source === "vimeo" && (
        <EtymologyVideoField
          name="video_url"
          label="Vimeo-link"
          type="url"
          required
          fullWidth
          disabled={disabled}
          resolveUrl={config.vimeoPreviewUrl}
        />
      )}
      {source === "upload" && (
        <Stack spacing={1}>
            <Button component="label" variant="outlined" disabled={disabled}>
            Videobestand kiezen
            <input
                type="file"
                accept="video/*"
                hidden
                disabled={disabled}
                onChange={(event) => {
                const selected = event.target.files?.[0];
                event.target.value = "";
                if (!selected) return;

                const maxBytes = config.maxUploadBytes || 250 * 1024 * 1024;

                if (!selected.size || selected.size > maxBytes) {
                    setFile(null);
                    setError("Kies een niet-leeg videobestand van maximaal 250 MB.");
                    return;
                }

                setFile(selected);
                setError("");
                }}
            />
            </Button>

            {file && <span>{file.name}</span>}
        </Stack>
        )}

        {source === "webcam" && !file && (
  <EtymologyCamera
    disabled={disabled}
    onRecorded={(recordedFile) => {
      const maxBytes = config.maxUploadBytes || 250 * 1024 * 1024;

      if (!recordedFile.size || recordedFile.size > maxBytes) {
        setError("De opname is leeg of groter dan 250 MB. Neem opnieuw op.");
        setSource("vimeo");
        return;
      }

      setFile(recordedFile);
      setError("");
    }}
    onCancel={() => {
      setFile(null);
      setSource(existingVideo ? "keep" : "vimeo");
    }}
  />
)}

{(source === "upload" || source === "webcam") && previewUrl && (
  <video
    src={previewUrl}
    controls
    playsInline
    style={{ width: "100%", maxHeight: 360, background: "#000" }}
  />
)}

{source === "webcam" && file && (
  <Button
    variant="outlined"
    disabled={disabled}
    onClick={() => setFile(null)}
  >
    Opnieuw opnemen
  </Button>
)}

        {error && <Alert severity="error">{error}</Alert>}

      <TextField
        name="text"
        label="Etymologietekst"
        defaultValue={pair?.texts?.[0]?.text || ""}
        multiline
        minRows={2}
        maxRows={8}
        disabled={disabled}
      />

      <FormControlLabel
        label="Gepubliceerd op WDB"
        control={
            <Checkbox
            checked={published}
            onChange={(event) => setPublished(event.target.checked)}
            disabled={disabled}
            sx={{
                color: "var(--heading-color, #303f6b)",
                "&.Mui-checked": {
                color: "var(--heading-color, #303f6b)",
                },
            }}
            />
        }
        />
      <Stack direction="row" spacing={1} justifyContent="flex-end">
        <Button onClick={onCancel} disabled={disabled}>
          Annuleren
        </Button>
        <Button
        type="submit"
        variant="contained"
        disabled={disabled}
        sx={primaryButtonSx}
        >
        Paar opslaan
        </Button>
      </Stack>
    </Stack>
  );
}