const uploadForm = document.getElementById("uploadForm");
const uploadStatus = document.getElementById("uploadStatus");
const resumeInput = document.getElementById("resume");
const fileLabel = document.getElementById("fileLabel");
const dropZone = document.getElementById("dropZone");

function setUploadState(message, isError = false) {
    if (!uploadStatus) {
        return;
    }
    uploadStatus.textContent = message;
    uploadStatus.classList.toggle("status-error", isError);
}

if (resumeInput) {
    resumeInput.addEventListener("change", () => {
        if (resumeInput.files[0]) {
            fileLabel.textContent = `Selected: ${resumeInput.files[0].name}`;
            setUploadState("Resume selected. Click Analyze Resume to continue.");
        }
    });
}

if (dropZone && resumeInput) {
    ["dragenter", "dragover"].forEach((eventName) => {
        dropZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropZone.classList.add("drag-active");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        dropZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropZone.classList.remove("drag-active");
        });
    });

    dropZone.addEventListener("drop", (event) => {
        const files = event.dataTransfer?.files;
        if (!files || !files.length) {
            return;
        }
        resumeInput.files = files;
        fileLabel.textContent = `Selected: ${files[0].name}`;
        setUploadState("Resume selected. Click Analyze Resume to continue.");
    });
}

if (uploadForm) {
    uploadForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        setUploadState("Analyzing resume. This may take a few seconds...");

        const formData = new FormData(uploadForm);

        try {
            const response = await fetch("/api/upload-resume", {
                method: "POST",
                body: formData,
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "Upload failed");
            }

            localStorage.setItem("analysisId", String(data.analysis_id));
            setUploadState("Analysis complete. Redirecting to dashboard...");
            window.location.href = "/dashboard";
        } catch (error) {
            setUploadState(error.message, true);
        }
    });
}
