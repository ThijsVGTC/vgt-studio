import React, { useEffect, useState } from "react";
import {
  Box,
  Button,
  Chip,
  MenuItem,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { FilterMenu } from "./signbank-list.jsx";

const filterLabels = {
  q: "Zoeken",
  status: "Status",
  recording_by: "Wie opname",
  recording_date: "Wanneer opname",
  review_status: "Opnamestatus",
  variant: "Variant",
};

const reviewOptions = [
  { value: "", text: "Alle opnamestatussen" },
  { value: "OPGENOMEN", text: "Opgenomen" },
  { value: "OVER-OPM", text: "Overgeslagen met opmerking" },
  { value: "OVER-AL_VIDEO", text: "Overgeslagen: bestaande video" },
  { value: "OPNAME_AFGEKEURD", text: "Opname afgekeurd" },
];

const sortOptions = [
  ["gloss:asc", "GLOSS A–Z"],
  ["gloss:desc", "GLOSS Z–A"],
  ["signbank_id:asc", "Signbank-ID oplopend"],
  ["signbank_id:desc", "Signbank-ID aflopend"],
  ["recording_date:asc", "Opnamedatum oplopend"],
  ["recording_date:desc", "Opnamedatum aflopend"],
];

function makeOptions(values, allLabel) {
  return [
    { value: "", text: allLabel },
    ...values.map((value) => ({
      value,
      text: value,
    })),
  ];
}

export function RecordingListFilters({
  data,
  onNavigate,
  loading = false,
}) {
  const filtersKey = JSON.stringify(data.filters);
  const [filters, setFilters] = useState(data.filters);

  useEffect(() => {
    setFilters(JSON.parse(filtersKey));
  }, [filtersKey]);

  function updateFilter(key, value) {
    setFilters((current) => ({
      ...current,
      [key]: value,
    }));
  }

  function submit(event) {
    event.preventDefault();

    onNavigate({
      ...filters,
      q: filters.q.trim(),
    });
  }

  function clearFilters() {
    onNavigate(
      Object.fromEntries(
        Object.keys(filterLabels).map((key) => [key, ""])
      )
    );
  }

  function filterMenu(key, label, options) {
    return (
      <FilterMenu
        label={label}
        options={options}
        value={[filters[key] || ""]}
        count={data.filters[key] ? 1 : 0}
        onChange={([value]) => updateFilter(key, value)}
        single
      />
    );
  }

  const activeFilters = Object.entries(data.filters).filter(
    ([key, value]) => filterLabels[key] && value
  );

  function displayValue(key, value) {
    if (key === "review_status") {
      return (
        reviewOptions.find((option) => option.value === value)?.text
        || value
      );
    }

    return value;
  }

  return (
    <Stack
    className="recording-sticky-controls"
  spacing={2}
  sx={{
    position: "sticky",
    top: 0,
    zIndex: 30,
    bgcolor: "background.default",
    py: 0.75,
  }}
>
      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Tabs
          value={data.tab}
          onChange={(_, value) => onNavigate({ tab: value })}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="Opnamelijsten"
        >
          {data.tabs.map((tab) => (
            <Tab
              key={tab.value}
              value={tab.value}
              disabled={loading}
              label={
                <Box
                  component="span"
                  sx={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 1,
                  }}
                >
                  {tab.label}

                  <Box
                    component="span"
                    sx={{
                      px: 0.75,
                      minWidth: 24,
                      border: "1px solid",
                      borderColor: "divider",
                      borderRadius: 10,
                      fontSize: "0.8rem",
                    }}
                  >
                    {tab.count}
                  </Box>
                </Box>
              }
            />
          ))}
        </Tabs>
      </Box>

      <Paper
        component="form"
        variant="outlined"
        onSubmit={submit}
        aria-label="Opnames filteren"
        sx={(theme) => ({
            p: 2,
            borderRadius: 2,
            bgcolor: alpha(theme.palette.primary.main, 0.08),
            borderColor: alpha(theme.palette.primary.main, 0.25),
            boxShadow: `0 6px 20px ${alpha(
                theme.palette.primary.main,
                0.07
            )}`,
            "& .signbank-filter-count": {
                bgcolor: "primary.main",
                color: "primary.contrastText",
            },
            'html[data-reading-mode="true"] &': {
                bgcolor: "background.paper",
                borderColor: "primary.main",
                boxShadow: "none",
            },
        })}
      >
        <Stack
          direction="row"
          useFlexGap
          flexWrap="wrap"
          spacing={1}
          sx={{ alignItems: "center" }}
        >
          <TextField
            size="small"
            type="search"
            label="Zoeken"
            placeholder="GLOSS, ID, vertaling, opmerking…"
            value={filters.q}
            onChange={(event) => updateFilter("q", event.target.value)}
          />

          {filterMenu(
            "status",
            "Status",
            makeOptions(data.options.statuses, "Alle statussen")
          )}

          {filterMenu(
            "recording_by",
            "Wie opname?",
            makeOptions(data.options.people, "Iedereen")
          )}

          {filterMenu(
            "recording_date",
            "Wanneer opname?",
            makeOptions(data.options.dates, "Alle datums")
          )}

          {filterMenu(
            "review_status",
            "Opnamestatus",
            reviewOptions
          )}

          {filterMenu(
            "variant",
            "Variant",
            makeOptions(data.options.variants, "Alle varianten")
          )}

          <Button
            type="submit"
            variant="contained"
            disableElevation
            disabled={loading}
          >
            Filteren
          </Button>

          <Button
            type="button"
            onClick={clearFilters}
            disabled={loading}
          >
            Wissen
          </Button>

          <TextField
            select
            size="small"
            label="Sorteren"
            value={`${data.sort}:${data.direction}`}
            disabled={loading}
            onChange={(event) => {
              const [sort, direction] = event.target.value.split(":");

              onNavigate({ sort, direction });
            }}
            sx={{ minWidth: 210 }}
          >
            {sortOptions.map(([value, label]) => (
              <MenuItem key={value} value={value}>
                {label}
              </MenuItem>
            ))}
          </TextField>
        </Stack>

        {activeFilters.length > 0 && (
          <Stack
            component="section"
            direction="row"
            useFlexGap
            flexWrap="wrap"
            spacing={1}
            aria-label="Actieve filters"
            sx={{ alignItems: "center", mt: 2 }}
          >
            <Box component="strong">Actieve filters</Box>

            {activeFilters.map(([key, value]) => (
              <Chip
                key={key}
                size="small"
                variant="outlined"
                label={`${filterLabels[key]}: ${displayValue(key, value)}`}
                aria-label={`Verwijder filter: ${filterLabels[key]}`}
                disabled={loading}
                onDelete={() => onNavigate({ [key]: "" })}
              />
            ))}
          </Stack>
        )}
      </Paper>
    </Stack>
  );
}