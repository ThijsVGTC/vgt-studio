import { createTheme } from "@mui/material/styles";

const primary = {
    main: "#303f6b",
    dark: "#253153",
    contrastText: "#ffffff",
};

export const studioThemes = {
    light: createTheme({
        palette: {
            mode: "light",
            primary,
        },
    }),

    dark: createTheme({
        palette: {
            mode: "dark",
            primary,
        },
    }),

    contrast: createTheme({
        palette: {
            mode: "dark",
            background: {
                default: "#000000",
                paper: "#121212",
            },
            text: {
                primary: "#FFFFFF",
                secondary: "#E5E5E5",
            },
            primary: {
                main: "#FFE500",
                dark: "#E6CE00",
                contrastText: "#000000",
            },
            divider: "#A6A6A6",
        },
    }),
};