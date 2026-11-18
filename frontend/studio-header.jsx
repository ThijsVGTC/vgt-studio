import React, { useLayoutEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
    AppBar, Button, Menu, MenuItem, Toolbar, Typography,Box,IconButton,Tooltip
} from "@mui/material";
import DarkModeOutlined from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlined from "@mui/icons-material/LightModeOutlined";
import VisibilityOutlined from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffOutlined from "@mui/icons-material/VisibilityOffOutlined";

const mount = document.getElementById("studio-react-header");
const links = mount.dataset;

function NavMenu({ label, items, active = false }) {
    const [anchor, setAnchor] = useState(null);
    const menuId = `studio-menu-${label.toLowerCase()}`;

    return (
        <>
            <Button
                color="inherit"
                aria-haspopup="menu"
                aria-expanded={Boolean(anchor)}
                aria-controls={anchor ? menuId : undefined}
                onClick={(event) => setAnchor(event.currentTarget)}
                sx={{ bgcolor: active ? "rgba(255,255,255,.18)" : undefined }}
            >
                {label} ▾
            </Button>

            <Menu
                id={menuId}
                anchorEl={anchor}
                open={Boolean(anchor)}
                onClose={() => setAnchor(null)}
            >
                {items.map(([name, href, current]) => (
                    <MenuItem
                        key={href}
                        component="a"
                        href={href}
                        selected={Boolean(current)}
                        aria-current={current ? "page" : undefined}
                    >
                        {name}
                    </MenuItem>
                ))}
            </Menu>
        </>
    );
}

function StudioHeader() {
    const [dark, setDark] = useState(
        () => localStorage.getItem("vgt-studio-theme") === "dark"
    );
    const [reading, setReading] = useState(
        () => localStorage.getItem("vgt-studio-reading") === "true"
    );

    useLayoutEffect(() => {
        document.getElementById("studio-header-fallback").hidden = true;
    }, []);

    useLayoutEffect(() => {
        const page = document.documentElement;
        page.dataset.theme = dark ? "dark" : "light";
        page.dataset.fontSize = reading ? "xlarge" : "normal";
        page.dataset.readingMode = String(reading);

        localStorage.setItem("vgt-studio-theme", page.dataset.theme);
        localStorage.setItem("vgt-studio-reading", String(reading));
    }, [dark, reading]);

    const view = links.view || "";
    const signbankActive =
        view.startsWith("signbank_") && !view.startsWith("signbank_export");
    const gebarometerActive = view.startsWith("gebarometer:");
    const themeLabel = dark ? "Lichte modus" : "Donkere modus";

    return (
        <AppBar position="static" elevation={0} sx={{ bgcolor: "#313f69" }}>
            <Toolbar sx={{ gap: 1.5, flexWrap: "wrap", py: 1 }}>
                <Button href={links.home} color="inherit" sx={{ fontWeight: 700 }}>
                    VGT STUDIO
                </Button>

                <Box sx={{ ml: "auto", display: "flex", gap: 1, alignItems: "center",
                        justifyContent: "flex-end", flexWrap: "wrap" }}>
                    <Box component="nav" aria-label="Hoofdnavigatie"
                        sx={{ display: "flex", gap: 1, justifyContent: "flex-end",
                            flexWrap: "wrap" }}>
                        <NavMenu label="Signbank" active={signbankActive} items={[
                            ["Signbank", links.signbank, view === "signbank_list"],
                            ["Stats", links.stats, view === "signbank_stats"],
                        ]} />
                        <NavMenu label="Opnames" active={!signbankActive && !gebarometerActive}
                                items={[
                            ["Opnames", links.recordings, view === "recording_list"],
                            ["Opnamereeksen", links.series, view === "recording_series_list"],
                            ["Videocontrole", links.review, view === "video_review_overview"],
                            ["Signbank Export", links.export, view === "signbank_export_preview"],
                        ]} />
                        <Button href={links.gebarometer} color="inherit"
                                aria-current={view === "gebarometer:overview" ? "page" : undefined}
                                sx={{ bgcolor: gebarometerActive ? "rgba(255,255,255,.18)" : undefined }}>
                            Gebarometer
                        </Button>
                    </Box>

                    <Tooltip title={themeLabel}>
                        <IconButton color="inherit" aria-label={themeLabel}
                                    onClick={() => setDark((value) => !value)}>
                            {dark ? <LightModeOutlined /> : <DarkModeOutlined />}
                        </IconButton>
                    </Tooltip>

                    <Tooltip title={reading ? "Leesmodus uitschakelen" : "Leesmodus inschakelen"}>
                        <IconButton color="inherit" aria-label="Leesmodus"
                                    aria-pressed={reading}
                                    onClick={() => setReading((value) => !value)}>
                            {reading ? <VisibilityOffOutlined /> : <VisibilityOutlined />}
                        </IconButton>
                    </Tooltip>

                    <Typography variant="body2">{links.username}</Typography>
                    <Button type="submit" form="studio-react-logout" color="inherit">
                        Uitloggen
                    </Button>
                </Box>
            </Toolbar>
        </AppBar>
    );

}

createRoot(mount).render(<StudioHeader />);