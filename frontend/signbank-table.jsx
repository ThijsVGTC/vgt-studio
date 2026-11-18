import React, { useEffect, useState } from "react";
import {
    Alert, Box, Link, Table, TableBody, TableCell,
    TableContainer, TableHead, TableRow, Typography,
} from "@mui/material";

export function SignbankTable({ listUrl }) {
    const [rows, setRows] = useState(null);
    const [error, setError] = useState(false);

    useEffect(() => {
        const controller = new AbortController();
        const url = new URL(listUrl, window.location.origin);
        url.search = window.location.search;
        url.searchParams.set("format", "json");

        setRows(null);
        setError(false);

        async function loadRows() {
            try {
                const response = await fetch(url, { signal: controller.signal });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);

                const data = await response.json();
                if (!controller.signal.aborted) setRows(data.rows);
            } catch (error) {
                if (!controller.signal.aborted) {
                    console.error("Signbank laden mislukt", error);
                    setError(true);
                }
            }
        }

        loadRows();
        return () => controller.abort();
    }, [listUrl]);

    if (error) return <Alert severity="error">De gebaren konden niet worden geladen.</Alert>;
    if (!rows) return <Typography role="status">Gebaren laden…</Typography>;

    return (
        <TableContainer>
            <Table size="small" aria-label="Signbank-tabel">
                <TableHead>
                    <TableRow>
                        <TableCell>GLOSS</TableCell>
                        <TableCell>Video</TableCell>
                        <TableCell>Handvorm</TableCell>
                    </TableRow>
                </TableHead>

                <TableBody>
                    {rows.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={3}>Geen gebaren gevonden.</TableCell>
                        </TableRow>
                    )}

                    {rows.map((row) => (
                        <TableRow key={row.id} hover>
                            <TableCell component="th" scope="row">
                                <Link href={row.detailUrl}>{row.gloss}</Link>
                            </TableCell>

                            <TableCell>
                                {row.thumbnailUrl && row.videoUrl ? (
                                    <Link href={row.videoUrl} target="_blank" rel="noopener">
                                        <Box component="img" src={row.thumbnailUrl}
                                             alt={`Video van ${row.gloss}`} loading="lazy"
                                             sx={{ display: "block", width: 120 }} />
                                    </Link>
                                ) : "–"}
                            </TableCell>

                            <TableCell>
                                <div className="signbank-handshape-flow">
                                    {row.handshapes.map(({ imageUrl, name }, index) => (
                                        <React.Fragment key={index}>
                                            {index > 0 && <span aria-hidden="true">→</span>}
                                            {imageUrl ? (
                                                <img src={imageUrl} alt={name}
                                                     loading="lazy"
                                                     className="signbank-handshape-image" />
                                            ) : <span>{name || "–"}</span>}
                                        </React.Fragment>
                                    ))}
                                </div>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
}