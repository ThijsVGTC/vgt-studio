import React, { useState } from "react";
import {
  Button,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

const KEEP = "__KEEP__";
const EMPTY = "__EMPTY__";
const NEW = "__NEW__";

const reviewOptions = [
  [KEEP, "Niet wijzigen"],
  [EMPTY, "Leeg maken / opnieuw opnemen"],
  ["OPGENOMEN", "Opgenomen"],
  ["OVER-OPM", "Overgeslagen met opmerking"],
  ["OVER-AL_VIDEO", "Overgeslagen: bestaande video"],
  ["OPNAME_AFGEKEURD", "Opname afgekeurd"],
];

function Hidden({ name, value }) {
  return (
    <input
      type="hidden"
      name={name}
      value={value ?? ""}
    />
  );
}

export function RecordingListActions({
  data,
  selectedItems,
  onSelectAll,
  onClearSelection,
  loading = false,
}) {
  const [scope, setScope] = useState("filtered");
  const [submitting, setSubmitting] = useState(false);

  const [bulk, setBulk] = useState({
    bulk_recording_by: KEEP,
    bulk_recording_date: KEEP,
    bulk_status: KEEP,
    bulk_review_status: KEEP,
  });

  const selectedCount = selectedItems.length;
  const busy = loading || submitting;

  const seriesItems =
    scope === "selected"
      ? selectedItems
      : data.matchingItems;

  const returnUrl = data.urls.list + window.location.search;

  function updateBulk(key, value) {
    setBulk((current) => ({
      ...current,
      [key]: value,
    }));
  }

  function submit(event, count) {
    if (busy || count === 0) {
      event.preventDefault();
      return;
    }

    setSubmitting(true);
  }

  function choice(name, label, options) {
    return (
      <TextField
        select
        size="small"
        name={name}
        label={label}
        value={bulk[name]}
        disabled={busy}
        onChange={(event) => updateBulk(name, event.target.value)}
        sx={{ minWidth: 190 }}
      >
        {options.map(([value, text]) => (
          <MenuItem key={value} value={value}>
            {text}
          </MenuItem>
        ))}
      </TextField>
    );
  }

  return (
    <Stack spacing={2}>
      <Stack
        direction="row"
        useFlexGap
        flexWrap="wrap"
        spacing={1}
        sx={{ alignItems: "center" }}
      >
        <Typography role="status" aria-live="polite">
          <strong>{selectedCount}</strong> geselecteerd
        </Typography>

        <Button
          variant="outlined"
          onClick={onSelectAll}
          disabled={busy || data.filteredCount === 0}
        >
          Alle {data.filteredCount} resultaten selecteren
        </Button>

        <Button
          onClick={onClearSelection}
          disabled={busy || selectedCount === 0}
        >
          Selectie wissen
        </Button>
      </Stack>

      <Paper
        component="form"
        method="post"
        action={data.urls.startSeries}
        onSubmit={(event) => submit(event, seriesItems.length)}
        variant="outlined"
        aria-label="Opnamereeks starten"
        sx={{
            p: 1.25,
            borderRadius: 2,
            alignSelf: "flex-start",
            maxWidth: "100%",
        }}
      >
        <Hidden name="csrfmiddlewaretoken" value={data.csrfToken} />

        <Hidden
          name="signbank_ids_csv"
          value={seriesItems.map((item) => item.signbankId).join(",")}
        />

        {Object.entries(data.filters).map(([key, value]) => (
          <Hidden key={key} name={key} value={value} />
        ))}

        <Hidden name="tab" value={data.tab} />
        <Hidden name="sort" value={data.sort} />
        <Hidden name="direction" value={data.direction} />

        <Stack
            direction="row"
            useFlexGap
            flexWrap="wrap"
            spacing={1}
            sx={{ alignItems: "center" }}
        >
          <Typography component="h2" variant="subtitle2" fontWeight={700}>
            Opnamereeks
          </Typography>

          <Stack
            direction="row"
            useFlexGap
            flexWrap="wrap"
            spacing={1}
            sx={{ alignItems: "center" }}
          >
            <TextField
              size="small"
              name="recording_series_name"
              label="Naam opnamereeks"
              placeholder="Bijvoorbeeld: Heropnames november"
              disabled={busy}
              slotProps={{
                htmlInput: { maxLength: 255 },
              }}
              sx={{ width: 220, maxWidth: "100%" }}
            />

            <TextField
              select
              size="small"
              label="Gebaren voor de reeks"
              value={scope}
              disabled={busy}
              onChange={(event) => setScope(event.target.value)}
              sx={{ width: 220, maxWidth: "100%" }}
            >
              <MenuItem value="filtered">
                Gefilterde lijst ({data.filteredCount})
              </MenuItem>

              <MenuItem
                value="selected"
                disabled={selectedCount === 0}
              >
                Alleen selectie ({selectedCount})
              </MenuItem>
            </TextField>

            <Button
              type="submit"
              variant="contained"
              disableElevation
              disabled={busy || seriesItems.length === 0}
            >
              Start opnamereeks ({seriesItems.length})
            </Button>

            <Button href={data.urls.seriesList}>
              Bestaande opnamereeksen
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Paper
        component="form"
        method="post"
        action={data.urls.bulkUpdate}
        onSubmit={(event) => submit(event, selectedCount)}
        variant="outlined"
        hidden={selectedCount === 0}
        aria-label="Opnames gezamenlijk aanpassen"
        sx={{
            p: 2,
            borderRadius: 2,
            display: selectedCount > 0 ? "block" : "none",
        }}
      >
        <Hidden name="csrfmiddlewaretoken" value={data.csrfToken} />
        <Hidden name="return_url" value={returnUrl} />
        <Hidden name="select_all" value="1" />

        <Hidden
          name="all_item_ids"
          value={selectedItems.map((item) => item.id).join(",")}
        />

        <Stack spacing={2}>
          <Typography component="h2" variant="h6" fontWeight={700}>
            Toepassen op selectie
          </Typography>

          <Stack
            direction="row"
            useFlexGap
            flexWrap="wrap"
            spacing={1}
            sx={{ alignItems: "center" }}
          >
            {choice(
              "bulk_recording_by",
              "Wie opname?",
              [
                [KEEP, "Niet wijzigen"],
                [EMPTY, "Naam wissen"],
                ...data.options.people.map((value) => [value, value]),
                [NEW, "+ Nieuwe naam"],
              ]
            )}

            {bulk.bulk_recording_by === NEW && (
              <TextField
                size="small"
                name="bulk_recording_by_new"
                label="Nieuwe naam"
                required
                disabled={busy}
                slotProps={{
                  htmlInput: { maxLength: 255 },
                }}
              />
            )}

            {choice(
              "bulk_recording_date",
              "Wanneer opname?",
              [
                [KEEP, "Niet wijzigen"],
                [EMPTY, "Datum wissen"],
                ...data.options.dates.map((value) => [value, value]),
                [NEW, "+ Nieuwe datum"],
              ]
            )}

            {bulk.bulk_recording_date === NEW && (
              <TextField
                size="small"
                type="date"
                name="bulk_recording_date_new"
                label="Nieuwe datum"
                required
                disabled={busy}
                slotProps={{
                  inputLabel: { shrink: true },
                }}
              />
            )}

            {choice(
              "bulk_status",
              "Status",
              [
                [KEEP, "Niet wijzigen"],
                [EMPTY, "Status wissen"],
                ...data.options.statuses.map((value) => [value, value]),
              ]
            )}

            {choice(
              "bulk_review_status",
              "Opnamestatus",
              reviewOptions
            )}

            <Button
              type="submit"
              variant="contained"
              disableElevation
              disabled={busy || selectedCount === 0}
            >
              Toepassen op {selectedCount} opnames
            </Button>
          </Stack>

          <Typography variant="body2" color="text.secondary">
            Alleen de gekozen velden worden aangepast.
          </Typography>
        </Stack>
      </Paper>
    </Stack>
  );
}