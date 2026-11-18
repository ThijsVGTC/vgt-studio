import React, { useLayoutEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
    AppBar, Button, Menu, MenuItem, Toolbar, Typography,
} from "@mui/material";

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

    return (
        <AppBar position="static" elevation={0} sx={{ bgcolor: "#313f69" }}>
            <Toolbar sx={{ gap: 1.5, flexWrap: "wrap", py: 1 }}>
                <Button href={links.home} color="inherit" sx={{ fontWeight: 700 }}>
                    VGT STUDIO
                </Button>

                <Toolbar
                    component="nav"
                    aria-label="Hoofdnavigatie"
                    disableGutters
                    variant="dense"
                    sx={{ gap: 1, flexWrap: "wrap", flexGrow: 1 }}
                >
                    <NavMenu label="Opnames" items={[
                        ["Opnames", links.recordings],
                        ["Opnamereeksen", links.series],
                        ["Videocontrole", links.review],
                        ["Signbank Export", links.export],
                    ]} />

                    <NavMenu label="Signbank" active items={[
                        ["Signbank", links.signbank, true],
                        ["Stats", links.stats],
                    ]} />

                    <Button href={links.gebarometer} color="inherit">
                        Gebarometer
                    </Button>
                </Toolbar>

                <Button
                    color="inherit"
                    aria-pressed={dark}
                    onClick={() => setDark((value) => !value)}
                >
                    Donkere modus
                </Button>

                <Button
                    color="inherit"
                    aria-pressed={reading}
                    onClick={() => setReading((value) => !value)}
                >
                    Leesmodus
                </Button>

                <Typography variant="body2">{links.username}</Typography>

                <Button type="submit" form="studio-react-logout" color="inherit">
                    Uitloggen
                </Button>
            </Toolbar>
        </AppBar>
    );
}

createRoot(mount).render(<StudioHeader />);