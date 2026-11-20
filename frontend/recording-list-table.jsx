import React, { useEffect, useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  Paper,
  Popover,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";

import {
  RECORDING_COLUMNS,
  RecordingCell,
} from "./recording-list-columns.jsx";

import { SignbankInfoDialog } from "./signbank-info-dialog.jsx";

const storageKey = "vgt-studio-recording-columns-v1";

function readPreferences() {
  try {
    const value = JSON.parse(
      localStorage.getItem(storageKey) || "{}"
    );

    return value && typeof value === "object" && !Array.isArray(value)
      ? value
      : {};
  } catch {
    return {};
  }
}

export function RecordingListTable({
  data,
  rows,
  selectedIds,
  onToggleSelection,
  onToggleVisible,
  onNavigate,
  loading = false,
}) {
  const theme = useTheme();

  const compact = useMediaQuery(
  theme.breakpoints.down("sm")
);

const fixedWidths = {
  gloss: compact ? 130 : 260,
  oldVideo: compact ? 100 : 156,
  action: compact ? 92 : 120,
};

function columnWidth(column) {
  return fixedWidths[column.id] ?? 180;
}

function pinnedStyle(column, header = false) {
  if (!column.required) return {};

  return {
    position: "sticky",
    left:
      column.id === "gloss"
        ? 0
        : column.id === "oldVideo"
          ? fixedWidths.gloss
          : undefined,
    right: column.id === "action" ? 0 : undefined,
    zIndex: header ? 4 : 2,
    bgcolor: header
      ? "primary.main"
      : "background.paper",
    boxShadow:
      column.id === "oldVideo"
        ? `4px 0 6px -4px ${theme.palette.divider}`
        : column.id === "action"
          ? `-4px 0 6px -4px ${theme.palette.divider}`
          : "none",
  };
}

  const [preferences, setPreferences] = useState(readPreferences);
  const [columnAnchor, setColumnAnchor] = useState(null);
  const [info, setInfo] = useState(null);

  useEffect(() => {
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify(preferences)
      );
    } catch {
      // De kolomkeuze blijft tijdens deze sessie bruikbaar.
    }
  }, [preferences]);

  function isVisible(column) {
    return (
      column.required ||
      (preferences[column.id] ?? !column.hidden)
    );
  }

  function toggleColumn(column) {
    if (column.required) return;

    setPreferences((current) => ({
      ...current,
      [column.id]: !(current[column.id] ?? !column.hidden),
    }));
  }

  const visibleColumns = RECORDING_COLUMNS.filter(isVisible);

  const allVisibleSelected =
    rows.length > 0 &&
    rows.every((row) => selectedIds.has(row.id));

  const someVisibleSelected = rows.some(
    (row) => selectedIds.has(row.id)
  );

  function changeSort(column) {
    onNavigate({
      sort: column.sort,
      direction:
        data.sort === column.sort && data.direction === "asc"
          ? "desc"
          : "asc",
    });
  }

  function heading(column) {
    const label = column.sort ? (
      <TableSortLabel
        active={data.sort === column.sort}
        direction={
          data.sort === column.sort
            ? data.direction
            : "asc"
        }
        disabled={loading}
        onClick={() => changeSort(column)}
        sx={{
          color: "inherit",
          "&:hover": { color: "inherit" },
          "&.Mui-active": { color: "inherit" },
          "&.Mui-active .MuiTableSortLabel-icon": {
            color: "inherit",
          },
        }}
      >
        {column.label}
      </TableSortLabel>
    ) : column.label;

    if (column.id !== "gloss") return label;

    return (
      <Stack
        direction="row"
        spacing={0.5}
        sx={{ alignItems: "center" }}
      >
        <Checkbox
          size="small"
          checked={allVisibleSelected}
          indeterminate={
            someVisibleSelected && !allVisibleSelected
          }
          disabled={loading || rows.length === 0}
          onChange={() => onToggleVisible(
            rows.map((row) => row.id)
          )}
          slotProps={{
            input: {
              "aria-label": "Selecteer alle geladen opnames",
            },
          }}
          sx={{
            color: "inherit",
            "&.Mui-checked": { color: "inherit" },
            "&.MuiCheckbox-indeterminate": {
              color: "inherit",
            },
          }}
        />

        {label}
      </Stack>
    );
  }

  return (
    <Stack spacing={1}>
      <Stack
        direction="row"
        sx={{ justifyContent: "flex-end" }}
      >
        <Button
          variant="outlined"
          aria-haspopup="dialog"
          aria-expanded={Boolean(columnAnchor)}
          onClick={(event) => setColumnAnchor(event.currentTarget)}
        >
          Kolommen kiezen
        </Button>
      </Stack>

      <Popover
        open={Boolean(columnAnchor)}
        anchorEl={columnAnchor}
        onClose={() => setColumnAnchor(null)}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        slotProps={{
          paper: {
            role: "dialog",
            "aria-label": "Zichtbare opnamekolommen",
            sx: { maxHeight: "75vh", maxWidth: "90vw" },
          },
        }}
      >
        <Stack sx={{ p: 2 }}>
          <Typography fontWeight={700} sx={{ mb: 1 }}>
            Zichtbare kolommen
          </Typography>

          {RECORDING_COLUMNS.map((column) => (
            <FormControlLabel
              key={column.id}
              label={
                column.required
                  ? `${column.label} (vast)`
                  : column.label
              }
              control={
                <Checkbox
                  size="small"
                  checked={Boolean(isVisible(column))}
                  disabled={Boolean(column.required)}
                  onChange={() => toggleColumn(column)}
                />
              }
            />
          ))}

          <Button
            onClick={() => setPreferences({})}
            sx={{ mt: 1 }}
          >
            Standaardkolommen herstellen
          </Button>
        </Stack>
      </Popover>

      <TableContainer
        component={Paper}
        variant="outlined"
        sx={{
          borderRadius: 2,
          maxWidth: "100%",
          overflowX: "auto",
        }}
      >
        <Table
          size="small"
          aria-label="Opnamelijst"
          aria-busy={loading}
            sx={{
            tableLayout: "fixed",
            width: visibleColumns.reduce(
                (sum, column) => sum + columnWidth(column),
                0
            ),
            borderCollapse: "separate",
            borderSpacing: 0,
            "& .MuiTableCell-root": {
                boxSizing: "border-box",
                py: 1.5,
                verticalAlign: "top",
            },
            }}
        >
            <colgroup>
            {visibleColumns.map((column) => (
                <col
                key={column.id}
                style={{ width: columnWidth(column) }}
                />
            ))}
            </colgroup>
          <TableHead>
            <TableRow>
              {visibleColumns.map((column) => (
                <TableCell
                  key={column.id}
                  sortDirection={
                    column.sort && data.sort === column.sort
                      ? data.direction
                      : false
                  }
                  sx={{
                    bgcolor: "primary.main",
                    color: "primary.contrastText",
                    fontWeight: 700,
                    whiteSpace: "nowrap",
                    ...pinnedStyle(column, true),
                    }}>
                  {heading(column)}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>

          <TableBody>
            {rows.map((row) => (
              <TableRow
                key={row.id}
                hover
                selected={selectedIds.has(row.id)}
                aria-selected={selectedIds.has(row.id)}
              >
                {visibleColumns.map((column) => (
                  <TableCell
                    key={column.id}
                    sx={{
                    width: columnWidth(column),
                    overflow: "hidden",
                    overflowWrap: "anywhere",
                    "& .MuiChip-root": {
                        maxWidth: "100%",
                    },
                    "& img": {
                        maxWidth: "100%",
                        height: "auto",
                    },
                    ...pinnedStyle(column),
                    }}
                  >
                    {column.id === "gloss" ? (
                      <Stack
                        direction="row"
                        spacing={0.5}
                        sx={{ alignItems: "flex-start" }}
                      >
                        <Checkbox
                          size="small"
                          checked={selectedIds.has(row.id)}
                          disabled={loading}
                          onChange={() => onToggleSelection(row.id)}
                          slotProps={{
                            input: {
                              "aria-label": `Selecteer ${row.gloss}`,
                            },
                          }}
                        />

                        <RecordingCell
                          row={row}
                          column={column.id}
                          onInfo={setInfo}
                        />
                      </Stack>
                    ) : (
                      <RecordingCell
                        row={row}
                        column={column.id}
                        onInfo={setInfo}
                      />
                    )}
                  </TableCell>
                ))}
              </TableRow>
            ))}

            {rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={visibleColumns.length}>
                  <Typography sx={{ py: 3, textAlign: "center" }}>
                    Geen opnames gevonden in deze tab met deze filters.
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {info && (
        <SignbankInfoDialog
          info={info}
          onClose={() => setInfo(null)}
          style={{
            "--create-heading":
              theme.palette.mode === "dark"
                ? theme.palette.background.paper
                : theme.palette.primary.main,
            "--create-surface": theme.palette.background.paper,
            "--create-accent-surface": alpha(
              theme.palette.primary.main,
              0.08
            ),
            "--create-border": theme.palette.divider,
            "--create-text": theme.palette.text.primary,
            "--create-action": theme.palette.primary.main,
            "--create-focus": theme.palette.primary.main,
          }}
        />
      )}
    </Stack>
  );
}