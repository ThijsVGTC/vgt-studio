import React, { useState } from "react";
import {
    Box, Button, Checkbox, Chip, FormControlLabel, Paper,
    Popover, Radio, Stack, TextField, Typography, MenuItem,
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
    const [query, setQuery] = useState(data.query);
    const [categories, setCategories] = useState(data.selectedCategories);
    const [functional, setFunctional] = useState(data.selectedFunctionalLabels);
    const [internal, setInternal] = useState(data.selectedInternalLabels);
    const [dictionary, setDictionary] = useState([data.inDictionary]);

    const options = (values) => values.map((value) => ({
        value,
        text: value === NO_LABEL ? "Geen label" : value,
    }));

    const internalOptions = options([NO_LABEL, ...data.internalLabels]);
    const dictionaryOptions = [
        { value: "", text: "Alles" },
        { value: "yes", text: "Ja" },
        { value: "no", text: "Nee" },
    ];

    const allInternalApplied = internalOptions.every((option) =>
        data.selectedInternalLabels.includes(option.value)
    );

    const chips = [
        ...(data.query ? [`Zoeken: ${data.query}`] : []),
        ...data.selectedCategories.map((value) => `Categorie: ${value}`),
        ...data.selectedFunctionalLabels.map((value) => `Functioneel: ${value}`),
        ...(allInternalApplied
            ? ["Alle interne labels en Geen label"]
            : data.selectedInternalLabels.length > 0
                ? data.selectedInternalLabels.map((value) =>
                    `Intern: ${value === NO_LABEL ? "Geen label" : value}`
                )
                : data.defaultHiddenLabels.map((value) =>
                    `Standaard verborgen: ${value.replaceAll("_", " ")}`
                )),
        ...(data.inDictionary
            ? [`In woordenboek: ${data.inDictionary === "yes" ? "Ja" : "Nee"}`]
            : []),
    ];

    function applyFilters(event) {
        event.preventDefault();

        const current = new URLSearchParams(window.location.search);
        const target = new URL(listUrl, window.location.href);
        const params = target.searchParams;

        for (const key of ["sort", "dir"]) {
            if (current.has(key)) params.set(key, current.get(key));
        }

        if (query.trim()) params.set("q", query.trim());
        if (dictionary[0]) params.set("in_dictionary", dictionary[0]);

        categories.forEach((value) => params.append("category", value));
        functional.forEach((value) => params.append("functional_label", value));
        internal.forEach((value) => params.append("internal_label", value));

        window.location.assign(target.href);
    }

    const appliedParams = new URLSearchParams(window.location.search);
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
                                count={data.selectedInternalLabels.length || data.defaultHiddenLabels.length}
                                onChange={setInternal} selectAll />

                    <FilterMenu label="In woordenboek" options={dictionaryOptions}
                                value={dictionary} count={data.inDictionary ? 1 : 0}
                                onChange={setDictionary} single />

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
                        {chips.map((label, index) => (
                            <Chip key={`${label}-${index}`} label={label}
                                  size="small" variant="outlined" />
                        ))}
                    </Box>
                )}
            </Paper>
        </>
    );
}