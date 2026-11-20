import React, { useEffect, useState } from "react";
import {
    Alert, Box, Button, Checkbox, Chip, Dialog, DialogContent, DialogTitle,
    FormControlLabel, Link, Popover, Stack, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, Typography, TableSortLabel,
} from "@mui/material";
import { SignbankEditDialog } from "./signbank-edit-dialog.jsx";

const columns = [
    { id: 1, label: "GLOSS", sortKey: "gloss" },
    { id: 2, label: "Video" },
    { id: 3, label: "Handvorm" },
    { id: 4, label: "Locatie" },
    { id: 5, label: "Mogelijke vertaling" },
    { id: 6, label: "Variant" },
    { id: 7, label: "Categorieën", sortKey: "categorie" },
    { id: 8, label: "Labels" },
    { id: 9, label: "Intern" },
    { id: 10, label: "Info" },
    { id: 11, label: "WDB" },
    { id: 12, label: "Actie", pinned: true },
];

const columnStorageKey = "vgt-studio-signbank-columns";

function readColumnPreferences() {
    try {
        return JSON.parse(localStorage.getItem(columnStorageKey) || "{}") || {};
    } catch {
        return {};
    }
}

function Badges({ items, functional = false }) {
    return (
            <Stack
                direction="row"
                useFlexGap
                flexWrap="wrap"
                spacing={1}
                sx={{ alignItems: "center", mb: 1 }}
            >
                <Button
                    size="small"
                    variant="outlined"
                    disabled={!selectedIds.length || addingRecordings}
                    onClick={addToRecordings}
                >
                    {addingRecordings
                        ? "Bezig met toevoegen…"
                        : "Toevoegen aan opnames"}
                </Button>

                <Typography variant="body2" role="status">
                    {selectedIds.length} geselecteerd
                </Typography>

                <Button
                    size="small"
                    variant="outlined"
                    disabled={!selectedIds.length || addingRecordings}
                    onClick={() => setSelected(new Set())}
                >
                    Selectie wissen
                </Button>

                <Stack
                    direction="row"
                    useFlexGap
                    flexWrap="wrap"
                    spacing={1}
                    sx={{ ml: "auto" }}
                >
                    <Button
                        size="small"
                        variant="outlined"
                        onClick={toggleHandshapes}
                    >
                        Handvormen · {showNames ? "Namen" : "Afbeeldingen"}
                    </Button>

                    <Button
                        size="small"
                        variant="outlined"
                        aria-haspopup="dialog"
                        aria-expanded={Boolean(columnAnchor)}
                        aria-controls={
                            columnAnchor ? "react-signbank-columns" : undefined
                        }
                        onClick={(event) =>
                            setColumnAnchor(event.currentTarget)
                        }
                    >
                        Kolommen kiezen
                    </Button>
                </Stack>
            </Stack>
    );
}

function EtymologyValue({ text }) {
    const embed = React.useRef(null);

    useEffect(() => {
        const match = text?.trim().match(
            /^https:\/\/(?:www\.|player\.)?vimeo\.com\/(?:video\/)?\d+(?:[/?#]|$)/i
        );

        if (!match || !window.Vimeo?.Player) return;

        const player = new window.Vimeo.Player(embed.current, {
            url: text.trim(),
            responsive: true,
        });

        player.ready().catch(() => {});
        return () => { player.destroy().catch(() => {}); };
    }, [text]);

    return (
        <Stack spacing={0.5}>
            <div ref={embed} />
            <Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>
                {text}
            </Typography>
        </Stack>
    );
}

export function SignbankTable({ listUrl, addRecordingsUrl, csrfToken, }) {
    const [rows, setRows] = useState(null);
    const [error, setError] = useState(false);
    const [loading, setLoading] = useState(true);
    const [nextPage, setNextPage] = useState(null);
    const [requestedPage, setRequestedPage] = useState(
        () => new URLSearchParams(window.location.search).get("page") || "1"
    );
    const [retry, setRetry] = useState(0);
    const loadMoreRef = React.useRef(null);
    const [showNames, setShowNames] = useState(
        () => localStorage.getItem("signbankHandshapeView") === "names"
    );
    const [columnPreferences, setColumnPreferences] = useState(readColumnPreferences);
    const [columnAnchor, setColumnAnchor] = useState(null);
    const [info, setInfo] = useState(null);
    const [editingRow, setEditingRow] = useState(null);
    const [selected, setSelected] = useState(() => new Set());
    const [addingRecordings, setAddingRecordings] = useState(false);
    const [recordingsError, setRecordingsError] = useState("");
    const addingRecordingsRef = React.useRef(false);

    const selectedIds = (rows ?? [])
        .filter((row) => selected.has(row.id))
        .map((row) => row.id);

    function toggleSelection(id) {
        setSelected((current) => {
            const next = new Set(current);

            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }

            return next;
        });
    }

    async function addToRecordings() {
        if (!selectedIds.length || addingRecordingsRef.current) return;

        addingRecordingsRef.current = true;
        setAddingRecordings(true);
        setRecordingsError("");

        try {
            const body = new URLSearchParams();

            for (const id of selectedIds) {
                body.append("signbank_ids", String(id));
            }

            const response = await fetch(addRecordingsUrl, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "Accept": "application/json",
                },
                body,
            });

            const contentType = response.headers.get("content-type") || "";

            if (!contentType.includes("application/json")) {
                throw new Error(
                    "Toevoegen kon niet worden bevestigd. " +
                    "Controleer de opnamelijst en vernieuw zo nodig deze pagina."
                );
            }

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(
                    result.error || "Toevoegen aan opnames is niet gelukt."
                );
            }

            window.location.assign(result.redirectUrl);
        } catch (error) {
            setRecordingsError(
                error.message ||
                "Toevoegen kon niet worden bevestigd. Controleer de opnamelijst."
            );
        } finally {
            addingRecordingsRef.current = false;
            setAddingRecordings(false);
        }
    }

    const visibleColumns = columns.filter(
        ({ id, pinned }) => pinned || id <= 2 || columnPreferences[id] !== false
    );

    const searchParams = new URLSearchParams(window.location.search);
    const currentSort = searchParams.get("sort");
    const currentDirection = searchParams.get("dir") === "desc" ? "desc" : "asc";

    function getSortUrl(sortKey) {
        const url = new URL(listUrl, window.location.origin);
        url.search = window.location.search;
        url.searchParams.set("sort", sortKey);
        url.searchParams.set(
            "dir",
            currentSort === sortKey && currentDirection === "asc" ? "desc" : "asc"
        );
        url.searchParams.delete("page");
        return url.href;
    }

    function toggleHandshapes() {
        const next = !showNames;
        setShowNames(next);
        localStorage.setItem("signbankHandshapeView", next ? "names" : "images");
    }

    function setColumnVisible(id, visible) {
        const next = { ...columnPreferences, [id]: visible };
        setColumnPreferences(next);
        localStorage.setItem(columnStorageKey, JSON.stringify(next));
    }

    useEffect(() => {
        const controller = new AbortController();
        const url = new URL(listUrl, window.location.origin);
        url.search = window.location.search;
        url.searchParams.set("format", "json");
        url.searchParams.set("page", requestedPage);

        async function loadRows() {
            try {
                const response = await fetch(url, { signal: controller.signal });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                if (controller.signal.aborted) return;

                setRows((previous) => {
                    const byId = new Map((previous ?? []).map((row) => [row.id, row]));

                    for (const row of data.rows) {
                        byId.set(row.id, row);
                    }

                    return [...byId.values()];
                });
                setNextPage(data.nextPage);
            } catch (error) {
                if (!controller.signal.aborted) {
                    console.error("Signbank laden mislukt", error);
                    setError(true);
                }
            } finally {
                if (!controller.signal.aborted) setLoading(false);
            }
        }

        loadRows();
        return () => controller.abort();
    }, [listUrl, requestedPage, retry]);

    const loadMore = React.useCallback(() => {
        if (loading || error || nextPage === null) return;

        setLoading(true);
        setRequestedPage(String(nextPage));
    }, [loading, error, nextPage]);

    useEffect(() => {
        const target = loadMoreRef.current;
        if (!target || loading || error || nextPage === null) return;
        if (!("IntersectionObserver" in window)) return;

        const observer = new IntersectionObserver(([entry]) => {
            if (entry.isIntersecting) {
                observer.disconnect();
                loadMore();
            }
        }, { rootMargin: "0px 0px 300px 0px" });

        observer.observe(target);
        return () => observer.disconnect();
    }, [loading, error, nextPage, loadMore]);

    useEffect(() => {
        const controller = new AbortController();

        async function refreshRow(event) {
            const id = String(event.detail.signbankId);
            const base = new URL(listUrl, window.location.origin);
            const url = new URL(`${encodeURIComponent(id)}/row/`, base);
            url.search = window.location.search;
            url.searchParams.set("format", "json");

            try {
                const response = await fetch(url, {
                    signal: controller.signal,
                    cache: "no-store",
                });

                if (!response.ok) throw new Error(`HTTP ${response.status}`);

                if (response.status === 204) {
                    setRows((current) =>
                        current?.filter((row) => String(row.id) !== id) ?? null
                    );
                    return;
                }

                const updatedRow = await response.json();
                if (controller.signal.aborted) return;

                setRows((current) =>
                    current?.map((row) =>
                        String(row.id) === id ? updatedRow : row
                    ) ?? null
                );
            } catch (error) {
                if (!controller.signal.aborted) {
                    console.error("Signbankrij bijwerken mislukt", error);
                }
            }
        }

        window.addEventListener("signbank:row-updated", refreshRow);

        return () => {
            controller.abort();
            window.removeEventListener("signbank:row-updated", refreshRow);
        };
    }, [listUrl]);

    function retryLoad() {
        setError(false);
        setLoading(true);
        setRetry((attempt) => attempt + 1);
    }

    if (error && !rows) {
        return (
            <Alert severity="error" action={
                <Button onClick={retryLoad}>Opnieuw proberen</Button>
            }>
                De gebaren konden niet worden geladen.
            </Alert>
        );
    }
    if (!rows) return <Typography role="status">Gebaren laden…</Typography>;

    function renderCell(row, id) {
        const infoActions = [
            ["Opm", "Opmerkingen", row.notes],
            ["Et", "Etymologie", row.etymology],
            ["Bron", "Bronnen", row.sources],
        ];

        switch (id) {
            case 1:
                return (
                    <Stack direction="row" spacing={0.5}
                           sx={{ alignItems: "center" }}>
                        <Checkbox
                            size="small"
                            checked={selected.has(row.id)}
                            disabled={addingRecordings}
                            onChange={() => toggleSelection(row.id)}
                            slotProps={{
                                input: {
                                    "aria-label": `Selecteer ${row.gloss}`,
                                },
                            }}
                        />
                        <Link href={row.detailUrl} fontWeight={600}>
                            {row.gloss}
                        </Link>
                    </Stack>
                );
            case 2:
                return row.thumbnailUrl && row.videoUrl ? (
                    <Link href={row.videoUrl} target="_blank" rel="noopener">
                        <Box component="img" src={row.thumbnailUrl}
                             alt={`Video van ${row.gloss}`} loading="lazy"
                             sx={{ display: "block", width: 120, height: "auto" }} />
                    </Link>
                ) : "–";
            case 3:
                return (
                    <div className="signbank-handshape-flow">
                        {row.handshapes.map(({ imageUrl, name }, index) => (
                            <React.Fragment key={index}>
                                {index > 0 && <span aria-hidden="true">→</span>}
                                {!showNames && imageUrl ? (
                                    <img src={imageUrl} alt={name} title={name}
                                         loading="lazy" className="signbank-handshape-image" />
                                ) : <span>{name || "–"}</span>}
                            </React.Fragment>
                        ))}
                    </div>
                );
            case 4:
                return (
                    <>
                        <div className="signbank-value-pair">
                            <span>Begin</span><span>{row.locations[0] || "–"}</span>
                        </div>
                        <div className="signbank-value-pair">
                            <span>Einde</span><span>{row.locations[1] || "–"}</span>
                        </div>
                    </>
                );
            case 5:
                return row.translations || "–";
            case 6:
                return <Badges items={row.variants} />;
            case 7:
                return row.categories.length ? <Badges items={row.categories} /> : "–";
            case 8:
                return <Badges items={row.functionalLabels} functional />;
            case 9:
                return <Badges items={row.internalLabels} />;
            case 10:
                return (
                    <Stack direction="row" useFlexGap flexWrap="wrap" spacing={0.5} sx={{ justifyContent: "flex-end" }}>
                        {infoActions.filter(([, , items]) => items?.length).map(([label, title, items]) => (
                            <Button key={label} size="small" variant="outlined"
                                    aria-label={`${title} voor ${row.gloss}`}
                                    onClick={() => setInfo({ title, items, row })}>
                                {label}
                            </Button>
                        ))}
                    </Stack>
                );
            case 11:
                return (
                    <Chip
                        size="small"
                        label={row.inDictionary ? "Ja" : "Nee"}
                        className={row.inDictionary ? "signbank-wdb-yes" : "signbank-wdb-no"}
                    />
                );
            case 12:
                return (
                    <Button
                        size="small"
                        variant="contained"
                        disableElevation
                        className="signbank-edit-button"
                        onClick={() => setEditingRow(row)}
                    >
                        Bewerken
                    </Button>
                );
            default:
                return null;
        }
    }

    return (
        <>
            <Stack direction="row" useFlexGap flexWrap="wrap" spacing={1}
                   sx={{ justifyContent: "flex-end", alignItems: "center", mb: 1 }}>
                                <Typography variant="body2" role="status">
                    {selectedIds.length} geselecteerd
                </Typography>

                <Button
                    size="small"
                    variant="outlined"
                    disabled={!selectedIds.length || addingRecordings}
                    onClick={() => setSelected(new Set())}
                >
                    Selectie wissen
                </Button>

                <Button
                    size="small"
                    variant="contained"
                    disableElevation
                    disabled={!selectedIds.length || addingRecordings}
                    onClick={addToRecordings}
                >
                    {addingRecordings
                        ? "Bezig met toevoegen…"
                        : "Toevoegen aan opnames"}
                </Button>
                <Button size="small" variant="outlined" onClick={toggleHandshapes}>
                    Handvormen · {showNames ? "Namen" : "Afbeeldingen"}
                </Button>
                <Button size="small" variant="outlined"
                        aria-haspopup="dialog"
                        aria-expanded={Boolean(columnAnchor)}
                        aria-controls={columnAnchor ? "react-signbank-columns" : undefined}
                        onClick={(event) => setColumnAnchor(event.currentTarget)}>
                    Kolommen kiezen
                </Button>
            </Stack>

            <Popover
                open={Boolean(columnAnchor)}
                anchorEl={columnAnchor}
                onClose={() => setColumnAnchor(null)}
                anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
                transformOrigin={{ vertical: "top", horizontal: "right" }}
                slotProps={{
                    paper: {
                        id: "react-signbank-columns",
                        role: "dialog",
                        "aria-label": "Zichtbare kolommen",
                    },
                }}
            >
                <Stack sx={{ p: 1.5 }}>
                    {columns.filter(({ id, pinned }) => id > 2 && !pinned).map(({ id, label }) => (
                        <FormControlLabel
                            key={id}
                            label={label}
                            control={
                                <Checkbox
                                    size="small"
                                    checked={columnPreferences[id] !== false}
                                    onChange={(event) => setColumnVisible(id, event.target.checked)}
                                />
                            }
                        />
                    ))}
                </Stack>
            </Popover>
            
            {recordingsError && (
                <Alert severity="error" sx={{ mb: 1 }}>
                    {recordingsError}
                </Alert>
            )}
            <TableContainer className="signbank-table-wrapper">
                <Table className="signbank-sticky-columns" size="small"
                       aria-label="Signbank-tabel"
                       sx={{ minWidth: "max-content", overflow: "visible" }}>
                    <TableHead>
                        <TableRow>
                            {visibleColumns.map(({ id, label, pinned, sortKey }) => {
                                const active = Boolean(sortKey && sortKey === currentSort);

                                return (
                                    <TableCell
                                        key={id}
                                        scope="col"
                                        className={pinned ? "signbank-pinned-action" : undefined}
                                        sortDirection={active ? currentDirection : false}
                                    >
                                        {sortKey ? (
                                            <TableSortLabel
                                                component="a"
                                                href={getSortUrl(sortKey)}
                                                active={active}
                                                direction={active ? currentDirection : "asc"}
                                            >
                                                {label}
                                            </TableSortLabel>
                                        ) : label}
                                    </TableCell>
                                );
                            })}
                        </TableRow>
                    </TableHead>

                    <TableBody>
                        {rows.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={visibleColumns.length}>
                                    Geen gebaren gevonden.
                                </TableCell>
                            </TableRow>
                        )}
                        {rows.map((row) => (
                            <TableRow key={row.id} hover>
                                {visibleColumns.map(({ id, pinned }) => (
                                    <TableCell
                                        key={id}
                                        className={pinned ? "signbank-pinned-action" : undefined}
                                        sx={id === 5 ? { minWidth: 180, maxWidth: 280 } : undefined}
                                    >
                                        {renderCell(row, id)}
                                    </TableCell>
                                ))}
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            <Stack ref={loadMoreRef} spacing={1} sx={{ alignItems: "center", py: 1.5 }}>
                {loading && (
                    <Typography role="status" variant="body2">
                        Meer gebaren laden…
                    </Typography>
                )}

                {error && (
                    <Alert severity="error" action={
                        <Button onClick={retryLoad}>Opnieuw proberen</Button>
                    }>
                        De volgende gebaren konden niet worden geladen.
                    </Alert>
                )}

                {!loading && !error && nextPage !== null && (
                    <Button variant="outlined" size="small" onClick={loadMore}>
                        Meer gebaren laden
                    </Button>
                )}
            </Stack>

            {editingRow && (
                <SignbankEditDialog
                    key={editingRow.id}
                    row={editingRow}
                    onClose={() => setEditingRow(null)}
                />
            )}
            {info && (
                <Dialog open onClose={() => setInfo(null)}
                        fullWidth maxWidth="sm" aria-labelledby="signbank-react-info-title">
                    <DialogTitle id="signbank-react-info-title">
                        {info.title} voor {info.row.gloss}
                    </DialogTitle>
                    <DialogContent>
                        <Stack spacing={1.5}>
                            {info.items.map((item, index) =>
                                info.title === "Etymologie" ? (
                                    <EtymologyValue key={index} text={item.text} />
                                ) : (
                                    <Typography key={index} sx={{ whiteSpace: "pre-wrap" }}>
                                        {item.type && <strong>{item.type} </strong>}
                                        {item.text}
                                    </Typography>
                                )
                            )}
                            <Button onClick={() => setInfo(null)} sx={{ alignSelf: "flex-end" }}>
                                Sluiten
                            </Button>
                        </Stack>
                    </DialogContent>
                </Dialog>
            )}
        </>
    );
}