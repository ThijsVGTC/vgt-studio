(() => {
    const state = window.signbankCreate;
    if (!state) return;

    const get = (name) =>
        document.getElementById(`signbank-create-${name}`);

    const modal = get("modal");
    const live = get("live");

    let stream = null;
    let recorder = null;
    let timer = null;
    let generation = 0;

    state.stopCamera = () => {
        generation++;
        clearInterval(timer);

        if (recorder) {
            recorder.ondataavailable = null;
            recorder.onstop = null;
            recorder.onerror = null;

            if (recorder.state !== "inactive") {
                recorder.stop();
            }

            recorder = null;
        }

        if (stream) {
            stream.getTracks().forEach((track) => track.stop());
            stream = null;
        }

        live.srcObject = null;
        get("timer").textContent = "00:00";
        get("start").disabled = true;
        get("stop").disabled = true;
    };

    get("webcam").addEventListener("click", async () => {
        state.showChoice();

        if (!navigator.mediaDevices?.getUserMedia ||
            !window.MediaRecorder) {
            state.showError(
                "Webcamopname is hier niet beschikbaar. " +
                "Open Studio via HTTPS in een recente browser."
            );
            return;
        }

        get("choice").hidden = true;
        get("camera").hidden = false;
        get("status").textContent = "Webcam openen…";

        const version = generation;

        try {
            const camera = await navigator.mediaDevices.getUserMedia({
                audio: false,
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    frameRate: { ideal: 30 },
                },
            });

            // Een late toestemmingsreactie mag de camera
            // na het sluiten van het venster niet aan laten.
            if (version !== generation || !modal.open) {
                camera.getTracks().forEach((track) => track.stop());
                return;
            }

            stream = camera;
            live.srcObject = stream;
            await live.play();

            if (version !== generation || !modal.open) return;

            get("start").disabled = false;
            get("status").textContent =
                "Zorg dat je handen en gezicht volledig in beeld zijn.";
        } catch (error) {
            if (version !== generation) return;

            state.showChoice();

            state.showError(
                error.name === "NotAllowedError"
                    ? "Geef de browser toestemming om je webcam te gebruiken."
                    : "De webcam kon niet worden geopend. " +
                      "Controleer of een andere app de camera gebruikt."
            );
        }
    });

    get("start").addEventListener("click", () => {
        if (!stream || recorder) return;

        const version = generation;
        const chunks = [];

        try {
            const mimeType = [
                "video/webm;codecs=vp9",
                "video/webm;codecs=vp8",
                "video/mp4",
                "video/webm",
            ].find((type) => MediaRecorder.isTypeSupported(type));

            const options = { videoBitsPerSecond: 2500000 };
            if (mimeType) options.mimeType = mimeType;

            recorder = new MediaRecorder(stream, options);
            const activeRecorder = recorder;

            recorder.ondataavailable = (event) => {
                if (event.data.size > 0) chunks.push(event.data);
            };

            recorder.onstop = () => {
                if (version !== generation || !modal.open) return;

                const type =
                    activeRecorder.mimeType ||
                    chunks[0]?.type ||
                    "video/webm";

                const extension = type.includes("mp4") ? "mp4" : "webm";

                const file = new File(
                    chunks,
                    `webcamopname.${extension}`,
                    { type }
                );

                state.showVideo(file);
            };

            recorder.onerror = () => {
                if (version !== generation) return;

                state.showChoice();
                state.showError(
                    "De opname is mislukt. Probeer opnieuw " +
                    "of upload een video."
                );
            };

            recorder.start(250);

            get("start").disabled = true;
            get("stop").disabled = false;
            get("stop").focus();
            get("status").textContent = "Opname loopt…";

            const startedAt = Date.now();

            timer = setInterval(() => {
                const seconds = Math.floor((Date.now() - startedAt) / 1000);

                get("timer").textContent =
                    String(Math.floor(seconds / 60)).padStart(2, "0") +
                    ":" +
                    String(seconds % 60).padStart(2, "0");
            }, 250);
        } catch (error) {
            state.showChoice();
            state.showError(
                "De opname kon niet worden gestart. " +
                "Probeer opnieuw of upload een video."
            );
        }
    });

    get("stop").addEventListener("click", () => {
        if (!recorder || recorder.state !== "recording") return;

        get("stop").disabled = true;
        get("status").textContent = "Opname voorbereiden om terug te kijken…";
        clearInterval(timer);
        recorder.stop();
    });

    get("camera-back").addEventListener("click", state.showChoice);

    window.addEventListener("pagehide", () => state.stopCamera());
})();