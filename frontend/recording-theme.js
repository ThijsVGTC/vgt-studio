import { createTheme } from "@mui/material/styles";
import { studioThemes } from "./studio-theme";

const recordingPrimary = {
  light: {
    main: "#924338",
    light: "#B96D61",
    dark: "#71342B",
    contrastText: "#FFFFFF",
  },
  dark: {
    main: "#E8AA9D",
    light: "#F2C7BE",
    dark: "#D78F80",
    contrastText: "#21100D",
  },
};

function createRecordingTheme(mode) {
  const base = studioThemes[mode];

  return createTheme(base, {
    palette: {
      primary:
        mode === "contrast"
          ? base.palette.primary
          : recordingPrimary[mode],
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: "none",
            fontWeight: 600,
            borderRadius: 8,
          },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            textTransform: "none",
            fontWeight: 700,
          },
        },
      },
    },
  });
}

export const recordingThemes = {
  light: createRecordingTheme("light"),
  dark: createRecordingTheme("dark"),
  contrast: createRecordingTheme("contrast"),
};