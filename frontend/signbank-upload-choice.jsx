import React from "react";
import { Button, Stack } from "@mui/material";

export function SignbankUploadChoice({ highContrast }) {
    return (
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <Button
                type="button"
                variant="contained"
                disableElevation
                onClick={() => document.getElementById("signbank-create-webcam").click()}
                sx={{
                    bgcolor: highContrast ? "#FFE500" : "#F3705D",
                    color: "#1B1412",
                    textTransform: "none",
                    "&:hover": {
                        bgcolor: highContrast ? "#FFF36A" : "#FF8978",
                    },
                }}
            >
                Webcamopname maken
            </Button>

            <Button
                type="button"
                variant="outlined"
                onClick={() => document.getElementById("signbank-create-upload").click()}
                sx={{ textTransform: "none" }}
            >
                Video uploaden
            </Button>
        </Stack>
    );
}