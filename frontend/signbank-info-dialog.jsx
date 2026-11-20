import React, { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Link,
  Stack,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { EtymologyPlayer } from "./etymology-pairs.jsx";

function TextItem({ item, source }) {
  const text = typeof item === "string" ? item : item.text || "";
  let href;

  if (source) {
    try {
      const url = new URL(text.trim());

      if (["https:", "http:"].includes(url.protocol)) {
        href = url.href;
      }
    } catch {
      // Een bron mag ook gewone tekst zijn.
    }
  }

  return (
    <Box
      sx={{
        p: 2,
        border: "1px solid var(--create-border)",
        borderRadius: 2,
      }}
    >
      {item.type && (
        <Typography
          component="h3"
          variant="subtitle2"
          fontWeight={700}
        >
          {item.type}
        </Typography>
      )}

      <Typography
        component="div"
        sx={{
          whiteSpace: "pre-wrap",
          overflowWrap: "anywhere",
        }}
      >
        {href ? (
          <Link
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            sx={{ color: "var(--create-action)" }}
          >
            {text}
          </Link>
        ) : (
          text
        )}
      </Typography>
    </Box>
  );
}

function EtymologyContent({ url }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    setData(null);
    setError("");

    async function load() {
      try {
        if (!url) {
          throw new Error("Geen etymologieadres beschikbaar.");
        }

        const response = await fetch(url, {
          credentials: "same-origin",
          cache: "no-store",
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });

        const result = await response.json();

        if (
          !response.ok ||
          !result.success ||
          !Array.isArray(result.pairs)
        ) {
          throw new Error("Etymologie ophalen mislukt.");
        }

        if (!controller.signal.aborted) {
          setData(result);
        }
      } catch {
        if (!controller.signal.aborted) {
          setError(
            "De etymologie kon niet worden geladen. Probeer opnieuw."
          );
        }
      }
    }

    load();

    return () => controller.abort();
  }, [url, attempt]);

  if (error) {
    return (
      <Alert
        severity="error"
        action={
          <Button onClick={() => setAttempt((value) => value + 1)}>
            Opnieuw proberen
          </Button>
        }
      >
        {error}
      </Alert>
    );
  }

  if (!data) {
    return <Typography role="status">Etymologie laden…</Typography>;
  }

  if (!data.pairs.length) {
    return <Typography>Nog geen etymologie toegevoegd.</Typography>;
  }

  return data.pairs.map((pair, index) => (
    <Box
      component="section"
      key={pair.pairNumber ?? index}
      sx={{
        p: 2,
        border: "1px solid var(--create-border)",
        borderRadius: 2,
      }}
    >
      <Stack spacing={1.5}>
        <Typography
          component="h3"
          variant="subtitle1"
          fontWeight={700}
        >
          Etymologie {pair.pairNumber ?? index + 1}
        </Typography>

        {pair.ambiguous && (
          <Alert severity="warning">
            Deze groep bevat meerdere notities. De koppeling moet
            nog worden nagekeken.
          </Alert>
        )}

        {pair.videos.map((video) => (
          <EtymologyPlayer
            key={video.id}
            url={video.text}
            resolveUrl={data.vimeoPreviewUrl}
          />
        ))}

        {pair.texts.map((text) => (
          <Typography
            key={text.id}
            sx={{
              whiteSpace: "pre-wrap",
              overflowWrap: "anywhere",
            }}
          >
            {text.text}
          </Typography>
        ))}
      </Stack>
    </Box>
  ));
}

export function SignbankInfoDialog({ info, onClose, style }) {
  const etymology = info.title === "Etymologie";

  return (
    <Dialog
      open
      onClose={onClose}
      fullWidth
      maxWidth={etymology ? "md" : "sm"}
      className="vgt-signbank-create-dialog"
      aria-labelledby="signbank-react-info-title"
      style={style}
    >
      <DialogTitle
        id="signbank-react-info-title"
        sx={{ pr: 7, overflowWrap: "anywhere" }}
      >
        {info.title} voor {info.row.gloss}

        <IconButton
          aria-label="Sluiten"
          onClick={onClose}
          sx={{
            position: "absolute",
            right: 12,
            top: 12,
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        <Stack spacing={2}>
          {etymology ? (
            <EtymologyContent url={info.row.etymologyPairsUrl} />
          ) : info.items.length ? (
            info.items.map((item, index) => (
              <TextItem
                key={item.id ?? index}
                item={item}
                source={info.title === "Bronnen"}
              />
            ))
          ) : (
            <Typography>Geen gegevens beschikbaar.</Typography>
          )}
        </Stack>
      </DialogContent>

      <DialogActions>
        <Button variant="outlined" onClick={onClose}>
          Sluiten
        </Button>
      </DialogActions>
    </Dialog>
  );
}