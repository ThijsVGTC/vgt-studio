import React from "react";
import {
  Box,
  Button,
  Chip,
  Link,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";

export const RECORDING_COLUMNS = [
  { id: "gloss", label: "GLOSS", required: true, sort: "gloss" },
  { id: "oldVideo", label: "Oude video", required: true },
  { id: "id", label: "Signbank-ID", hidden: true, sort: "signbank_id" },
  { id: "handshape", label: "Handvorm", hidden: true },
  { id: "location", label: "Locatie", hidden: true },
  { id: "translation", label: "Mogelijke vertaling", hidden: true },
  { id: "variant", label: "Variant" },
  { id: "categories", label: "Categorieën", hidden: true },
  { id: "labels", label: "Labels", hidden: true },
  { id: "date", label: "Opnamedatum", sort: "recording_date" },
  { id: "person", label: "Wie opname?" },
  { id: "status", label: "Status", hidden: true },
  { id: "review", label: "Opnamestatus" },
  { id: "videoReview", label: "Videocontrole" },
  { id: "export", label: "Export naar Signbank" },
  { id: "newVideo", label: "Nieuwe video", hidden: true },
  { id: "remarks", label: "Opmerkingen", hidden: true },
  { id: "series", label: "Opnamereeksen", hidden: true },
  { id: "info", label: "Info Signbank" },
  { id: "dictionary", label: "WDB", hidden: true },
  { id: "action", label: "Actie", required: true },
];

const dateFormat = new Intl.DateTimeFormat("nl-BE", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "Europe/Brussels",
});

function formatDate(value) {
  return value ? dateFormat.format(new Date(value)) : "";
}

function Badges({ items = [] }) {
  if (!items.length) return "–";

  return (
    <Stack direction="row" useFlexGap flexWrap="wrap" spacing={0.5}>
      {items.map((item, index) => {
        const text = typeof item === "string" ? item : item.short || item.name;

        return (
          <Chip
            key={index}
            size="small"
            variant="outlined"
            label={text}
            title={typeof item === "string" ? undefined : item.name}
          />
        );
      })}
    </Stack>
  );
}

function Text({ children }) {
  return (
    <Typography
      variant="body2"
      sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
    >
      {children || "–"}
    </Typography>
  );
}

export function RecordingCell({ row, column, onInfo }) {
  const signbank = row.signbank;

  switch (column) {
    case "gloss":
      return (
        <Stack spacing={0.5}>
          <Link
            href={row.signbankUrl || row.recordingUrl}
            fontWeight={700}
            sx={{ overflowWrap: "anywhere" }}
          >
            {row.gloss || "(zonder GLOSS)"}
          </Link>

          {row.hasSignbankEntry ? (
            <Tooltip
              title={
                row.signbankSyncedAt
                  ? `Gesynchroniseerd: ${formatDate(row.signbankSyncedAt)}`
                  : "Gekoppeld aan Signbank"
              }
            >
              <Typography variant="caption" color="text.secondary">
                Signbank gekoppeld
              </Typography>
            </Tooltip>
          ) : (
            <Chip
              size="small"
              variant="outlined"
              label="Zonder Signbank-entry"
            />
          )}

          {row.state.overdue && (
            <Chip size="small" variant="outlined" label="Datum verstreken" />
          )}

          {row.state.invalidDate && (
            <Chip size="small" variant="outlined" label="Datum controleren" />
          )}

          {row.state.needsRetake && (
            <Chip size="small" variant="outlined" label="Heropname nodig" />
          )}
        </Stack>
      );

    case "oldVideo":
      if (!row.oldVideoUrl) return "–";

      return (
        <Link
          href={row.oldVideoUrl}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Oude video van ${row.gloss} bekijken`}
        >
          {row.thumbnailUrl ? (
            <Box
              component="img"
              src={row.thumbnailUrl}
              alt={`Oude video van ${row.gloss}`}
              loading="lazy"
              sx={{ display: "block", width: 120, borderRadius: 1 }}
            />
          ) : (
            "Oude video bekijken"
          )}
        </Link>
      );

    case "id":
      return row.signbankId;

    case "handshape":
      return signbank ? (
        <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
          {signbank.handshapes.map((shape, index) => (
            <React.Fragment key={index}>
              {index > 0 && <span aria-hidden="true">→</span>}

              {shape.imageUrl ? (
                <Box
                  component="img"
                  src={shape.imageUrl}
                  alt={shape.name || "Handvorm"}
                  title={shape.name}
                  loading="lazy"
                  sx={{ width: 42, height: 42, objectFit: "contain" }}
                />
              ) : (
                <span>{shape.name || "–"}</span>
              )}
            </React.Fragment>
          ))}
        </Stack>
      ) : "–";

    case "location":
      return signbank ? (
        <Stack spacing={0.25}>
          <Text>Begin: {signbank.locations[0] || "–"}</Text>
          <Text>Einde: {signbank.locations[1] || "–"}</Text>
        </Stack>
      ) : "–";

    case "translation":
      return <Text>{signbank?.translations}</Text>;

    case "variant":
      return <Badges items={signbank?.variants} />;

    case "categories":
      return <Badges items={signbank?.categories} />;

    case "labels":
      return (
        <Badges
          items={[
            ...(signbank?.functionalLabels || []),
            ...(signbank?.internalLabels || []),
          ]}
        />
      );

    case "date":
      return <Text>{row.recordingDate}</Text>;

    case "person":
      return <Text>{row.recordingBy}</Text>;

    case "status":
      return <Text>{row.status}</Text>;

    case "review":
      return <Chip size="small" variant="outlined" label={row.reviewLabel} />;

    case "videoReview":
      return (
        <Tooltip title={row.videoReviewRemarks || row.videoReviewLabel}>
          <Chip
            size="small"
            variant="outlined"
            label={row.videoReviewLabel}
          />
        </Tooltip>
      );

    case "export":
      return (
        <Stack spacing={0.5}>
          <Chip
            size="small"
            variant="outlined"
            label={row.exported ? "Verwerkt" : "Niet verwerkt"}
          />

          {row.exportedAt && (
            <Typography variant="caption" color="text.secondary">
              Laatste export: {formatDate(row.exportedAt)}
            </Typography>
          )}
        </Stack>
      );

    case "newVideo":
      return row.newVideoUrl ? (
        <Link href={row.newVideoUrl} target="_blank" rel="noopener noreferrer">
          Nieuwe video bekijken
        </Link>
      ) : "–";

    case "remarks":
      return <Text>{row.remarks}</Text>;

    case "series":
      return row.series.length ? (
        <Stack spacing={0.5}>
          {row.series.map((series) => (
            <Link key={series.id} href={series.reportUrl}>
              {series.name}
            </Link>
          ))}
        </Stack>
      ) : "–";

    case "info": {
      if (!signbank) return "–";

      const notes = signbank.notes || [];
      const etymologyTexts = notes.filter(
        (item) => item.type?.trim().toLowerCase() === "etymology_text"
      );

      const actions = [
        [
          "Opm",
          "Opmerkingen",
          notes.filter(
            (item) => item.type?.trim().toLowerCase() !== "etymology_text"
          ),
        ],
        [
          "Et",
          "Etymologie",
          [...(signbank.etymology || []), ...etymologyTexts],
        ],
        ["Bron", "Bronnen", signbank.sources || []],
      ];

      return (
        <Stack direction="row" useFlexGap flexWrap="wrap" spacing={0.5}>
          {actions
            .filter(([, , items]) => items.length > 0)
            .map(([label, title, items]) => (
              <Button
                key={label}
                size="small"
                variant="outlined"
                aria-label={`${title} voor ${row.gloss}`}
                onClick={() => onInfo({ title, items, row: signbank })}
              >
                {label}
              </Button>
            ))}
        </Stack>
      );
    }

    case "dictionary":
      return signbank ? (
        <Chip
          size="small"
          variant="outlined"
          label={signbank.inDictionary ? "Ja" : "Nee"}
        />
      ) : "–";

    case "action":
      return (
        <Button
          href={row.recordingUrl}
          size="small"
          variant="contained"
          disableElevation
        >
          Opname
        </Button>
      );

    default:
      return "–";
  }
}