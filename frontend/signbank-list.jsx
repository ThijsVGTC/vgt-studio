import React, { useState } from "react";
import {
    Box, Button, Checkbox, Chip, FormControlLabel, Paper,
    Popover, Radio, Stack, Switch, TextField, Typography, MenuItem,
} from "@mui/material";

const NO_LABEL = "__geen_label__";
const formatNumber = new Intl.NumberFormat("nl-BE");

function FilterMenu({
    label, options, value, count, onChange, selectAll = false, single = false,
}) {
    const [anchor, setAnchor] = useState(null);
    const [search, setSearch] = useState("");
    const visibleOptions = options.filter(({ text }) =>
        text.toLowerCase().includes(search.trim().toLowerCase())
    );
    const allChecked = options.length > 0 &&
        options.every((option) => value.includes(option.value));

    function selectOption(optionValue) {
        if (single) {
            onChange([optionValue]);
            setAnchor(null);
        } else {
            onChange(value.includes(optionValue)
                ? value.filter((item) => item !== optionValue)
                : [...value, optionValue]);
        }
    }

    return (
        <>
            <Button
                type="button"
                variant="outlined"
                aria-haspopup="dialog"
                aria-expanded={Boolean(anchor)}
                onClick={(event) => setAnchor(event.currentTarget)}
                sx={{ gap: 0.75, textTransform: "none" }}
            >
                {label}
                {count > 0 && <span className="signbank-filter-count">{count}</span>}
            </Button>

            <Popover
                open={Boolean(anchor)}
                anchorEl={anchor}
                onClose={() => {
                    setAnchor(null);
                    setSearch("");
                }}
                anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
                slotProps={{ paper: { role: "dialog", "aria-label": label } }}
            >
                <Stack sx={{ p: 1.25, width: 260, maxWidth: "calc(100vw - 32px)" }}>
                    {!single && (
                        <TextField
                            size="small"
                            label={`Zoeken in ${label.toLowerCase()}`}
                            value={search}
                            onChange={(event) => setSearch(event.target.value)}
                        />
                    )}

                    {selectAll && (
                        <FormControlLabel
                            label="Alles selecteren"
                            control={
                                <Checkbox
                                    size="small"
                                    checked={allChecked}
                                    indeterminate={!allChecked && value.length > 0}
                                    onChange={() => onChange(
                                        allChecked ? [] : options.map((option) => option.value)
                                    )}
                                />
                            }
                        />
                    )}

                    <Box sx={{ maxHeight: 250, overflowY: "auto" }}>
                        {visibleOptions.map((option) => (
                            <FormControlLabel
                                key={option.value}
                                sx={{ display: "flex", mx: 0 }}
                                label={option.text}
                                control={single ? (
                                    <Radio
                                        size="small"
                                        checked={value.includes(option.value)}
                                        onChange={() => selectOption(option.value)}
                                    />
                                ) : (
                                    <Checkbox
                                        size="small"
                                        checked={value.includes(option.value)}
                                        onChange={() => selectOption(option.value)}
                                    />
                                )}
                            />
                        ))}
                        {visibleOptions.length === 0 && (
                            <Typography variant="body2" sx={{ p: 1 }}>
                                Geen opties gevonden.
                            </Typography>
                        )}
                    </Box>
                </Stack>
            </Popover>
        </>
    );
}

const sortOptions = [
    ["signbank_id:asc", "Signbank-ID oplopend"],
    ["signbank_id:desc", "Signbank-ID aflopend"],
    ["gloss:asc", "GLOSS A–Z"],
    ["gloss:desc", "GLOSS Z–A"],
    ["categorie:asc", "Categorieën A–Z"],
    ["categorie:desc", "Categorieën Z–A"],
];

export function SignbankListControls({ data, listUrl, totalCount, highContrast }) {
    const appliedParams = new URLSearchParams(window.location.search);
    const explicitExclusions = appliedParams.get("internal_mode") === "exclude";
    const useExclusions = explicitExclusions || data.selectedInternalLabels.length === 0;
    const hiddenLabels = explicitExclusions
        ? appliedParams.getAll("hidden_internal_label")
        : data.defaultHiddenLabels;

    const normalizeLabel = (value) => value.trim().toLowerCase();
    const hiddenKeys = new Set(hiddenLabels.map(normalizeLabel));
    const internalValues = [...new Set([NO_LABEL, ...data.internalLabels])];

    const [query, setQuery] = useState(data.query);
    const [categories, setCategories] = useState(data.selectedCategories);
    const [functional, setFunctional] = useState(data.selectedFunctionalLabels);
    const [internal, setInternal] = useState(() =>
        useExclusions
            ? internalValues.filter((value) => !hiddenKeys.has(normalizeLabel(value)))
            : data.selectedInternalLabels
    );
    const [dictionary, setDictionary] = useState([data.inDictionary]);
    const [hasEtymology, setHasEtymology] = useState(Boolean(data.hasEtymology));

    const labelText = (value) =>
        value === NO_LABEL ? "Geen label" : value.replaceAll("_", " ");

    const options = (values) => values.map((value) => ({
        value,
        text: labelText(value),
    }));

    const internalOptions = options(internalValues);
    const dictionaryOptions = [
        { value: "", text: "Alles" },
        { value: "yes", text: "Ja" },
        { value: "no", text: "Nee" },
    ];

    const internalCount = useExclusions
        ? hiddenKeys.size
        : data.selectedInternalLabels.length;

    function writeExclusions(params, labels) {
        params.delete("internal_label");
        params.delete("hidden_internal_label");
        params.set("internal_mode", "exclude");

        for (const label of labels) {
            params.append("hidden_internal_label", label);
        }
    }

    function removeFilter(key, value) {
        const target = new URL(listUrl, window.location.href);
        target.search = window.location.search;
        const params = target.searchParams;
        params.delete("page");

        if (key === "hidden_internal_label") {
            writeExclusions(params, hiddenLabels.filter(
                (label) => normalizeLabel(label) !== normalizeLabel(value)
            ));
        } else if (key === "q" || key === "in_dictionary") {
            params.delete(key);
        } else {
            const remaining = params.getAll(key).filter((item) => item.trim() !== value);
            params.delete(key);
            remaining.forEach((item) => params.append(key, item));
        }

        window.location.assign(target.href);
    }

    const chips = [
        ...(data.query ? [["q", data.query, `Zoeken: ${data.query}`]] : []),
        ...data.selectedCategories.map((value) => [
            "category", value, `Categorie: ${value}`,
        ]),
        ...data.selectedFunctionalLabels.map((value) => [
            "functional_label", value, `Functioneel: ${value}`,
        ]),
        ...(useExclusions
            ? hiddenLabels.map((value) => [
                "hidden_internal_label",
                value,
                `${explicitExclusions ? "Verborgen" : "Standaard verborgen"}: ${labelText(value)}`,
            ])
            : data.selectedInternalLabels.map((value) => [
                "internal_label", value, `Intern: ${labelText(value)}`,
            ])),
        ...(data.inDictionary ? [[
            "in_dictionary",
            data.inDictionary,
            `In woordenboek: ${data.inDictionary === "yes" ? "Ja" : "Nee"}`,
        ]] : []),
        ...(data.hasEtymology
        ? [["has_etymology", "yes", "Heeft etymologie"]]
        : []),
    ];

    function applyFilters(event) {
        event.preventDefault();

        const target = new URL(listUrl, window.location.href);
        const params = target.searchParams;

        for (const key of ["sort", "dir"]) {
            if (appliedParams.has(key)) params.set(key, appliedParams.get(key));
        }

        if (query.trim()) params.set("q", query.trim());
        if (dictionary[0]) params.set("in_dictionary", dictionary[0]);
        if (hasEtymology) params.set("has_etymology", "yes");

        categories.forEach((value) => params.append("category", value));
        functional.forEach((value) => params.append("functional_label", value));

        const checked = new Set(internal);
        const unchecked = internalValues.filter((value) => !checked.has(value));
        const defaultKeys = new Set(data.defaultHiddenLabels.map(normalizeLabel));
        const isDefault = unchecked.length === defaultKeys.size
            && unchecked.every((value) => defaultKeys.has(normalizeLabel(value)));

        if (!isDefault) {
            const narrowedSelection = unchecked.some(
                (value) => !hiddenKeys.has(normalizeLabel(value))
            );

            if (internal.length === 0 || unchecked.length === 0 ||
                (useExclusions && !narrowedSelection)) {
                writeExclusions(params, unchecked);
            } else {
                internal.forEach((value) => params.append("internal_label", value));
            }
        }

        window.location.assign(target.href);
    }
    const activeSort = appliedParams.get("sort") || "signbank_id";
    const activeDirection = appliedParams.get("dir") === "desc" ? "desc" : "asc";
    const sortValue = `${activeSort}:${activeDirection}`;
    const selectedSort = sortOptions.some(([value]) => value === sortValue)
        ? sortValue
        : "signbank_id:asc";

    function changeSort(event) {
        const [sort, direction] = event.target.value.split(":");
        const url = new URL(listUrl, window.location.origin);
        url.search = window.location.search;
        url.searchParams.set("sort", sort);
        url.searchParams.set("dir", direction);
        url.searchParams.delete("page");
        window.location.assign(url.href);
    }

    const primarySx = {
        bgcolor: highContrast ? "#ffe500" : "#313f69",
        color: "#261511",
        textTransform: "none",
        "&:hover": { bgcolor: highContrast ? "#fff36a" : "#253153" },
    };

    return (
        <>
            <Stack direction="row" sx={{
                alignItems: "center", justifyContent: "space-between",
                flexWrap: "wrap", gap: 1, mb: 1,
            }}>
                <Typography component="h1" variant="h4" sx={{ fontWeight: 700 }}>
                    Signbank
                </Typography>

                <Stack direction="row" sx={{ alignItems: "center", flexWrap: "wrap", gap: 1 }}>
                    <Typography variant="body2">
                        <strong>{formatNumber.format(data.filteredCount)} resultaten</strong>
                        {" / "}{formatNumber.format(totalCount)} totaal
                    </Typography>

                    {data.canCreate && (
                        <Button type="button" data-signbank-create
                                variant="contained" disableElevation sx={primarySx}>
                            + Nieuw gebaar toevoegen
                        </Button>
                    )}
                </Stack>
            </Stack>

            <Paper component="form" variant="outlined" onSubmit={applyFilters}
                   className="signbank-filter-form">
                <Stack direction="row" sx={{
                    alignItems: "center", flexWrap: "wrap", gap: 0.75,
                }}>
                    <TextField size="small" type="search" label="Zoeken"
                               placeholder="GLOSS, ID, vertaling…"
                               value={query}
                               onChange={(event) => setQuery(event.target.value)} />

                    <FilterMenu label="Categorieën" options={options(data.categories)}
                                value={categories} count={data.selectedCategories.length}
                                onChange={setCategories} />

                    <FilterMenu label="Functionele labels" options={options(data.functionalLabels)}
                                value={functional} count={data.selectedFunctionalLabels.length}
                                onChange={setFunctional} selectAll />

                    <FilterMenu label="Interne labels" options={internalOptions}
                                value={internal}
                                count={internalCount}
                                onChange={setInternal} selectAll />

                    <FilterMenu label="In woordenboek" options={dictionaryOptions}
                                value={dictionary} count={data.inDictionary ? 1 : 0}
                                onChange={setDictionary} single />
                    
                    <FormControlLabel
                    label="Etymologie"
                    sx={{ mx: 0 }}
                    control={
                        <Switch
                        checked={hasEtymology}
                        onChange={(event) => setHasEtymology(event.target.checked)}
                        color="primary"
                        />
                    }
                    />

                    <Button type="submit" variant="contained" disableElevation sx={primarySx}>
                        Filteren
                    </Button>

                    <Button href={listUrl} sx={{ textTransform: "none" }}>Wissen</Button>
                    <TextField
                        select
                        size="small"
                        label="Sorteren"
                        value={selectedSort}
                        onChange={changeSort}
                        sx={{ minWidth: 195 }}
                    >
                        {sortOptions.map(([value, label]) => (
                            <MenuItem key={value} value={value}>
                                {label}
                            </MenuItem>
                        ))}
                    </TextField>
                </Stack>

                {chips.length > 0 && (
                    <Box component="section" className="signbank-active-filters"
                         aria-label="Actieve filters">
                        <strong>Actieve filters</strong>
                        {chips.map(([key, value, label]) => (
                            <Chip
                                key={`${key}-${value}`}
                                label={label}
                                aria-label={`Verwijder filter: ${label}`}
                                size="small"
                                variant="outlined"
                                onDelete={() => removeFilter(key, value)}
                            />
                        ))}
                    </Box>
                )}
            </Paper>
        </>
    );
}