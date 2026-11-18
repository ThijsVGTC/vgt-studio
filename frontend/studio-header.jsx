import React, { useLayoutEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
    AppBar, Button, Menu, MenuItem, Toolbar, Typography,Box,IconButton,Tooltip, ThemeProvider
} from "@mui/material";
import DarkModeOutlined from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlined from "@mui/icons-material/LightModeOutlined";
import VisibilityOutlined from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffOutlined from "@mui/icons-material/VisibilityOffOutlined";
import { studioThemes } from "./studio-theme";
import { createPortal } from "react-dom";
import { SignbankUploadChoice } from "./signbank-upload-choice.jsx";

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
        const page = document.documentElement;
        page.dataset.theme = dark ? "dark" : "light";
        page.dataset.fontSize = reading ? "contrast" : "normal";
        page.dataset.readingMode = String(reading);

        localStorage.setItem("vgt-studio-theme", page.dataset.theme);
        localStorage.setItem("vgt-studio-reading", String(reading));
    }, [dark, reading]);

    const view = links.view || "";
    const signbankActive =
        view.startsWith("signbank_") && !view.startsWith("signbank_export");
    const gebarometerActive = view.startsWith("gebarometer:");
    const themeLabel = dark ? "Lichte modus" : "Donkere modus";
    const iconSx = {
        width: 44,
        height: 44,
        "& .MuiSvgIcon-root": { fontSize: "1.125rem" },
    };

    const theme = studioThemes[reading ? "contrast" : dark ? "dark" : "light"];
    const displayUsername = (links.username ?? "").replace(
        /^./u,
        (letter) => letter.toLocaleUpperCase("nl-BE")
    );
    const uploadChoice = document.getElementById("signbank-react-upload-choice");

    return (
        <ThemeProvider theme={theme}>
            <AppBar position="static" elevation={0} sx={{ bgcolor: reading ? "#000000" : "#313f69" }}>
                <Toolbar
                    disableGutters
                    sx={{
                        position: "relative",
                        flexDirection: "column",
                        alignItems: "stretch",
                        justifyContent: "center",
                        gap: 0.5,
                        py: 1,
                    }}
                >
                    <Box className="container" sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        flexWrap: "wrap",
                        gap: 1,
                    }}>
                        <Button href={links.home} color="inherit" sx={{ fontWeight: 700 }}>
                            VGT STUDIO
                        </Button>

                        <Box sx={{
                            ml: "auto",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "flex-end",
                            flexWrap: "wrap",
                            gap: 0.5,
                        }}>
                            <Box component="nav" aria-label="Hoofdnavigatie"
                                sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                                <NavMenu label="Signbank" active={signbankActive} items={[
                                    ["Signbank", links.signbank, view === "signbank_list"],
                                    ["Stats", links.stats, view === "signbank_stats"],
                                ]} />
                                <NavMenu label="Opnames"
                                        active={!signbankActive && !gebarometerActive}
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
                                            sx={iconSx} onClick={() => setDark(!dark)}>
                                    {dark ? <LightModeOutlined /> : <DarkModeOutlined />}
                                </IconButton>
                            </Tooltip>

                            <Tooltip title={reading ? "Hoog contrast uitschakelen" : "Hoog contrast inschakelen"}>
                                <IconButton color="inherit" aria-label="Leesmodus"
                                            aria-pressed={reading} sx={{
                                                ...iconSx,
                                                ...(reading && {
                                                    bgcolor: "#FFE500",
                                                    color: "#000000",
                                                    "&:hover": { bgcolor: "#FFF36A" },
                                                }),
                                            }}
                                            onClick={() => setReading(!reading)}>
                                    {reading ? <VisibilityOffOutlined /> : <VisibilityOutlined />}
                                </IconButton>
                            </Tooltip>
                        </Box>
                    </Box>

                    <Box role="group" aria-label="Account" sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        pl: 1.5,
                        mr: 3,
                        alignSelf: "flex-end",
                        borderLeft: "1px solid rgba(255,255,255,.35)",
                        "@media (min-width: 1800px)": {
                            position: "absolute",
                            right: 24,
                            top: "50%",
                            transform: "translateY(-50%)",
                            mr: 0,
                        },
                    }}>
                        <Typography sx={{ fontSize: "0.8125rem" }}>
                            {displayUsername}
                        </Typography>
                        <Button type="submit" form="studio-react-logout"
                                variant="contained" disableElevation size="small"
                                sx={{
                                    bgcolor: "#F3705D",
                                    color: "#261511",
                                    fontSize: "0.75rem",
                                    textTransform: "none",
                                    "&:hover": { bgcolor: "#FF8978" },
                                }}>
                            Uitloggen
                        </Button>
                    </Box>
                </Toolbar>
            </AppBar>
            {uploadChoice && createPortal(
                <SignbankUploadChoice highContrast={reading} />,
                uploadChoice
            )}
        </ThemeProvider>
    );
}

createRoot(mount).render(<StudioHeader />);