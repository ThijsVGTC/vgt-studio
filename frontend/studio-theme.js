import { createTheme } from "@mui/material/styles";

export const studioThemes = {
    light: createTheme({
        palette: { mode: "light" },
    }),
    dark: createTheme({
        palette: { mode: "dark" },
    }),
    contrast: createTheme({
        palette: {
            mode: "dark",
            background: { default: "#000000", paper: "#121212" },
            text: { primary: "#FFFFFF", secondary: "#E5E5E5" },
            primary: { main: "#FFE500", contrastText: "#000000" },
            divider: "#A6A6A6",
        },
    }),
};