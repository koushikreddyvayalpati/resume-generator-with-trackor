/**
 * Resume Generator Application
 * Auto-validation with modern UX
 */

class ResumeGenerator {
    constructor() {
        this.contentInput = document.getElementById("contentInput");
        this.companyNameInput = document.getElementById("companyName");
        this.folderNameInput = document.getElementById("folderName");
        this.generateBtn = document.getElementById("generateBtn");
        this.downloadBtn = document.getElementById("downloadBtn");
        this.openFolderBtn = document.getElementById("openFolderBtn");
        this.refreshBtn = document.getElementById("refreshBtn");
        this.retryBtn = document.getElementById("retryBtn");

        // Validation
        this.validationDisplay = document.getElementById("validationDisplay");
        this.validationStatus = document.getElementById("validationStatus");
        this.errorsList = document.getElementById("errorsList");
        this.warningsList = document.getElementById("warningsList");

        // States
        this.initialState = document.getElementById("initialState");
        this.loadingState = document.getElementById("loadingState");
        this.successState = document.getElementById("successState");
        this.errorState = document.getElementById("errorState");

        // Modal - Instructions
        this.instructionsModal = document.getElementById("instructionsModal");
        this.instructionsBtn = document.getElementById("instructionsBtn");
        this.closeModalBtn = document.getElementById("closeModal");
        this.modalOverlay = document.getElementById("modalOverlay");

        // Modal - Settings
        this.settingsModal = document.getElementById("settingsModal");
        this.settingsBtn = document.getElementById("settingsBtn");
        this.settingsClose = document.getElementById("settingsClose");
        this.settingsCancel = document.getElementById("settingsCancel");
        this.settingsSave = document.getElementById("settingsSave");
        this.settingsModalOverlay = document.getElementById("settingsModalOverlay");
        this.outputDirInput = document.getElementById("outputDirInput");
        this.browseBtn = document.getElementById("browseBtn");
        this.dirPickerInput = document.getElementById("dirPickerInput");

        // Modal - Profile
        this.profileModal = document.getElementById("profileModal");
        this.profileBtn = document.getElementById("profileBtn");
        this.profileClose = document.getElementById("profileClose");
        this.profileCancel = document.getElementById("profileCancel");
        this.profileSave = document.getElementById("profileSave");
        this.profileModalOverlay = document.getElementById("profileModalOverlay");
        this.profileName = document.getElementById("profileName");
        this.profileLocation = document.getElementById("profileLocation");
        this.profilePhone = document.getElementById("profilePhone");
        this.profileEmail = document.getElementById("profileEmail");
        this.profileCertifications = document.getElementById("profileCertifications");
        this.profileProjects = document.getElementById("profileProjects");

        // Base resume for local parsing
        this.baseResume = null;
        this.loadBaseResume();

        // Event listeners
        this.contentInput.addEventListener("input", () => this.onContentChange());
        this.contentInput.addEventListener("keydown", (e) => this.handleContentKeydown(e));
        this.folderNameInput.addEventListener("keydown", (e) => this.handleFolderKeydown(e));
        this.generateBtn.addEventListener("click", () => this.generate());
        this.downloadBtn.addEventListener("click", () => this.download());
        this.openFolderBtn.addEventListener("click", () => this.openGeneratedFolder());
        this.refreshBtn.addEventListener("click", () => this.checkStatus());
        this.retryBtn.addEventListener("click", () => this.reset());
        this.instructionsBtn.addEventListener("click", () => this.openModal());
        this.closeModalBtn.addEventListener("click", () => this.closeModal());
        this.modalOverlay.addEventListener("click", () => this.closeModal());

        this.settingsBtn.addEventListener("click", () => this.openSettings());
        this.settingsClose.addEventListener("click", () => this.closeSettings());
        this.settingsCancel.addEventListener("click", () => this.closeSettings());
        this.settingsModalOverlay.addEventListener("click", () => this.closeSettings());
        this.settingsSave.addEventListener("click", () => this.saveSettings());
        this.browseBtn.addEventListener("click", () => this.browseDirectory());
        this.dirPickerInput.addEventListener("change", (e) => this.handleDirectorySelection(e));

        this.profileBtn.addEventListener("click", () => this.openProfile());
        this.profileClose.addEventListener("click", () => this.closeProfile());
        this.profileCancel.addEventListener("click", () => this.closeProfile());
        this.profileModalOverlay.addEventListener("click", () => this.closeProfile());
        this.profileSave.addEventListener("click", () => this.saveProfile());

        // Drag and drop support for directory input
        this.outputDirInput.addEventListener("dragover", (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.outputDirInput.style.borderColor = "var(--primary)";
            this.outputDirInput.style.backgroundColor = "#f0f7ff";
        });

        this.outputDirInput.addEventListener("dragleave", (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.outputDirInput.style.borderColor = "var(--gray-300)";
            this.outputDirInput.style.backgroundColor = "white";
        });

        this.outputDirInput.addEventListener("drop", (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.outputDirInput.style.borderColor = "var(--gray-300)";
            this.outputDirInput.style.backgroundColor = "white";
            this.handleDirectoryDrop(e);
        });

        this.statusPath = null;
        this.pdfPath = null;
        this.outputDir = null;
        this.statusCheckInterval = null;
        this.validationTimeout = null;
        this.isGenerating = false;

        // Initial state
        this.showState("initial");
    }

    async loadBaseResume() {
        try {
            const response = await fetch("/config/base_resume.json");
            this.baseResume = await response.json();
        } catch (error) {
            console.error("Failed to load base resume:", error);
            this.baseResume = {};
        }
    }

    // Auto-validate and preview with debounce
    onContentChange() {
        const content = this.contentInput.value.trim();
        this.updateCharCount();

        // Clear previous timeout
        clearTimeout(this.validationTimeout);

        // Show preview immediately if there's content
        if (content) {
            // Load preview immediately
            this.loadPreview(content);

            // Debounce validation
            this.validationTimeout = setTimeout(() => this.validate(), 500);
        } else {
            this.validationDisplay.style.display = "none";
            this.generateBtn.disabled = true;
            document.getElementById("previewContainer").style.display = "none";
        }
    }

    handleContentKeydown(e) {
        // Shift+Enter from content input -> focus company name
        if (e.shiftKey && e.key === "Enter") {
            if (this.isGenerating) return;
            e.preventDefault();
            this.companyNameInput.focus();
        }
    }

    handleFolderKeydown(e) {
        // Shift+Enter from folder name input -> generate
        if (e.shiftKey && e.key === "Enter") {
            if (this.isGenerating) return;
            e.preventDefault();
            this.generate();
        }
    }

    updateCharCount() {
        const count = this.contentInput.value.length;
        document.getElementById("charCount").textContent = count;
    }

    async validate() {
        const content = this.contentInput.value.trim();

        if (!content) {
            this.generateBtn.disabled = true;
            return;
        }

        try {
            const response = await fetch("/api/validate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content }),
            });

            const data = await response.json();

            // Update validation display
            this.showValidationStatus(data.valid, data.errors, data.warnings);

            // Enable/disable generate button based on validation
            this.generateBtn.disabled = !data.valid;
        } catch (error) {
            console.error("Validation error:", error);
            this.generateBtn.disabled = true;
        }
    }

    async loadPreview(content) {
        if (!this.baseResume) return;
        const preview = parseUpdatedContentToResume(content, this.baseResume);
        const validation = validateUpdatedContent(content);
        this.displayPreview(preview);
        if (validation.errors.length > 0) {
            this.showValidationStatus(false, validation.errors, validation.warnings);
        }
    }

    displayPreview(preview) {
        const container = document.getElementById("previewContainer");
        console.log("Display preview called, container:", container);
        console.log("Preview data:", preview);

        // Helper function to apply bold formatting
        const applyBold = (text) => {
            return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        };

        let html = '<div class="preview-content">';

        // Title
        if (preview.title) {
            const boldTitle = applyBold(preview.title);
            html += `<div class="preview-section"><h3 class="preview-title">${boldTitle}</h3></div>`;
        }

        // Summary
        if (preview.summary) {
            const boldSummary = applyBold(preview.summary);
            html += `<div class="preview-section">
                <h4 class="preview-heading">SUMMARY</h4>
                <p class="preview-text">${boldSummary}</p>
            </div>`;
        }

        // Skills
        if (preview.technical_skills && preview.technical_skills.length > 0) {
            html += `<div class="preview-section">
                <h4 class="preview-heading">TECHNICAL SKILLS</h4>
                <div class="preview-skills">`;
            preview.technical_skills.forEach(skill => {
                const boldItems = applyBold(skill.items);
                html += `<div class="skill-item"><strong>${skill.category}:</strong> ${boldItems}</div>`;
            });
            html += '</div></div>';
        }

        // Experience
        if (preview.experience && preview.experience.length > 0) {
            html += '<div class="preview-section"><h4 class="preview-heading">PROFESSIONAL EXPERIENCE</h4>';
            preview.experience.forEach(exp => {
                if (exp.company || exp.title) {
                    html += `<div class="preview-experience">
                        <div class="exp-header">
                            <strong>${exp.company}</strong> | ${exp.dates}
                        </div>
                        <div class="exp-title">${exp.title}</div>
                        <div class="exp-bullets">`;

                    if (exp.bullets && exp.bullets.length > 0) {
                        // Show ALL bullets, with **bold** support
                        exp.bullets.forEach(bullet => {
                            const boldBullet = applyBold(bullet);
                            html += `<div class="bullet">• ${boldBullet}</div>`;
                        });
                    } else {
                        html += '<div class="bullet-none">⚠️ No bullets found for this company</div>';
                    }

                    html += '</div></div>';
                }
            });
            html += '</div>';
        }

        html += '</div>';

        container.innerHTML = html;
        container.style.display = "block";
    }

    openModal() {
        this.instructionsModal.style.display = "flex";
        document.body.style.overflow = "hidden";
    }

    closeModal() {
        this.instructionsModal.style.display = "none";
        document.body.style.overflow = "auto";
    }

    async openSettings() {
        try {
            const response = await fetch("/api/settings");
            const settings = await response.json();
            this.outputDirInput.value = settings.output_directory || "";
            this.settingsModal.style.display = "flex";
            document.body.style.overflow = "hidden";
        } catch (error) {
            console.error("Failed to load settings:", error);
        }
    }

    closeSettings() {
        this.settingsModal.style.display = "none";
        document.body.style.overflow = "auto";
    }

    formatProjects(projects) {
        return (projects || [])
            .map((project) => {
                const bullets = (project.bullets || [])
                    .map((bullet) => `- ${bullet}`)
                    .join("\n");
                return [project.name || "", bullets].filter(Boolean).join("\n");
            })
            .filter(Boolean)
            .join("\n\n");
    }

    parseProjects(text) {
        const blocks = text
            .split(/\n\s*\n/)
            .map((block) => block.trim())
            .filter(Boolean);

        return blocks
            .map((block) => {
                const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
                const name = lines.shift() || "";
                const bullets = lines
                    .map((line) => line.replace(/^[-•●]\s*/, "").trim())
                    .filter(Boolean);
                return { name, bullets };
            })
            .filter((project) => project.name);
    }

    async openProfile() {
        try {
            const response = await fetch("/api/profile");
            const profile = await response.json();
            this.profileName.value = profile.name || "";
            this.profileLocation.value = profile.contact?.location || "";
            this.profilePhone.value = profile.contact?.phone || "";
            this.profileEmail.value = profile.contact?.email || "";
            this.profileCertifications.value = (profile.certifications || []).join("\n");
            this.profileProjects.value = this.formatProjects(profile.projects || []);
            this.profileModal.style.display = "flex";
            document.body.style.overflow = "hidden";
        } catch (error) {
            console.error("Failed to load profile:", error);
            alert("Could not load profile settings.");
        }
    }

    closeProfile() {
        this.profileModal.style.display = "none";
        document.body.style.overflow = "auto";
    }

    async saveProfile() {
        const payload = {
            name: this.profileName.value.trim(),
            contact: {
                location: this.profileLocation.value.trim(),
                phone: this.profilePhone.value.trim(),
                email: this.profileEmail.value.trim(),
            },
            certifications: this.profileCertifications.value
                .split("\n")
                .map((line) => line.trim())
                .filter(Boolean),
            projects: this.parseProjects(this.profileProjects.value),
        };

        this.profileSave.disabled = true;
        try {
            const response = await fetch("/api/profile", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (data.success) {
                this.closeProfile();
            } else {
                alert(`Error: ${data.error || "Failed to save profile"}`);
            }
        } catch (error) {
            console.error("Profile save error:", error);
            alert("Failed to save profile.");
        } finally {
            this.profileSave.disabled = false;
        }
    }

    async saveSettings() {
        const outputDirectory = this.outputDirInput.value.trim();

        if (!outputDirectory) {
            alert("Please enter a valid output directory path");
            return;
        }

        this.settingsSave.disabled = true;

        try {
            const response = await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ output_directory: outputDirectory }),
            });

            const data = await response.json();

            if (data.success) {
                alert("Settings saved successfully!");
                this.closeSettings();
            } else {
                alert(`Error: ${data.error || "Failed to save settings"}`);
            }
        } catch (error) {
            console.error("Error saving settings:", error);
            alert("Failed to save settings. Please try again.");
        } finally {
            this.settingsSave.disabled = false;
        }
    }

    async browseDirectory() {
        try {
            const response = await fetch("/api/select-output-directory", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({}),
            });
            const data = await response.json();
            if (data.success) {
                this.outputDirInput.value = data.output_directory;
            } else if (!data.cancelled) {
                alert(`Could not open folder picker: ${data.error || "Unknown error"}`);
            }
        } catch (error) {
            console.error("Directory picker error:", error);
            alert("Could not open the folder picker. Enter the full folder path manually.");
        }
    }

    handleDirectorySelection(event) {
        const files = event.target.files;

        if (files.length === 0) {
            return;
        }

        // webkitRelativePath gives us paths like "folder-name/file1.txt"
        // Extract the root folder name from the first file's path
        const firstFilePath = files[0].webkitRelativePath || files[0].name;
        const pathParts = firstFilePath.split('/');

        if (pathParts.length > 0) {
            const dirName = pathParts[0];
            // Show alert with the directory name found
            alert(`Found directory: "${dirName}"\n\nPlease enter the FULL absolute path to this directory.\n\nExample: /Users/yourname/Documents/${dirName}`);
            console.log("Selected directory name:", dirName, `(containing ${files.length} files)`);
        } else {
            alert("Please select a directory, not a file");
        }

        // Reset the file input so the same directory can be selected again
        this.dirPickerInput.value = "";
    }

    handleDirectoryDrop(event) {
        const items = event.dataTransfer.items;

        if (!items || items.length === 0) {
            return;
        }

        // Get the first dropped item
        const item = items[0];

        if (item.kind === "file") {
            const entry = item.webkitGetAsEntry();

            if (entry && entry.isDirectory) {
                // Try to get the full path from the directory entry
                const fullPath = entry.fullPath;

                if (fullPath && fullPath !== "/") {
                    this.outputDirInput.value = fullPath;
                    console.log("Dropped directory path:", fullPath);
                } else {
                    // Fallback to just showing the name
                    const dirName = entry.name;
                    alert(`Dropped directory: "${dirName}"\n\nPlease enter the FULL absolute path to this directory.\n\nExample: /Users/yourname/Documents/${dirName}`);
                    this.outputDirInput.value = dirName;
                }
            } else {
                alert("Please drop a folder, not a file");
            }
        }
    }

    showValidationStatus(valid, errors, warnings) {
        // Update status badge
        this.validationStatus.className = valid ? "status-badge valid" : "status-badge invalid";
        this.validationStatus.textContent = valid ? "✓ Valid" : "✕ Invalid";

        // Update errors
        if (errors.length > 0) {
            this.errorsList.innerHTML = errors
                .map((err) => `<div>${err}</div>`)
                .join("");
            this.validationDisplay.style.display = "block";
        } else {
            this.validationDisplay.style.display = "none";
        }
    }

    async generate() {
        const content = this.contentInput.value.trim();
        const companyName = this.companyNameInput.value.trim();
        const folderName = this.folderNameInput.value.trim();

        if (!content) {
            this.showError("Please paste resume content first");
            return;
        }

        this.isGenerating = true;
        this.generateBtn.disabled = true;
        this.contentInput.disabled = true;
        this.companyNameInput.disabled = true;
        this.folderNameInput.disabled = true;
        this.showState("loading");

        try {
            const payload = { content };
            if (companyName) {
                payload.company_name = companyName;
            }
            if (folderName) {
                payload.folder_name = folderName;
            }

            const response = await fetch("/api/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            if (data.success) {
                this.statusPath = data.status_path;
                this.pdfPath = data.pdf;
                this.outputDir = data.output_dir;

                // Show success state and start polling
                this.showState("success");
                this.startStatusPolling();
            } else {
                this.showError(data.error || "Generation failed");
                this.showState("error");
            }
        } catch (error) {
            this.showError(error.message);
            this.showState("error");
        } finally {
            this.isGenerating = false;
            this.generateBtn.disabled = false;
            this.contentInput.disabled = false;
            this.companyNameInput.disabled = false;
            this.folderNameInput.disabled = false;
        }
    }

    startStatusPolling() {
        let pollCount = 0;
        const maxPolls = 150;
        const startTime = Date.now();

        // Show proper loading UI
        const previewSection = document.getElementById("previewSection");
        const statusPDF = document.getElementById("statusPDF");

        if (previewSection) previewSection.style.display = "block";
        if (statusPDF) {
            statusPDF.innerHTML = '<span class="spinner"></span> Generating PDF... Please wait';
        }

        const pdfPreview = document.getElementById("pdfPreview");
        if (pdfPreview) {
            pdfPreview.src = "";
            pdfPreview.style.display = "none";
        }

        this.statusCheckInterval = setInterval(async () => {
            pollCount++;
            const elapsedSec = Math.floor((Date.now() - startTime) / 1000);

            // Update elapsed time
            if (statusPDF) {
                statusPDF.innerHTML = `<span class="spinner"></span> Generating PDF... ${elapsedSec}s`;
            }

            if (pollCount > maxPolls) {
                clearInterval(this.statusCheckInterval);
                this.showRefreshOption();
                return;
            }

            try {
                const response = await fetch(
                    `/api/status?path=${encodeURIComponent(this.statusPath)}`
                );
                const status = await response.json();

                if (status.state === "success") {
                    clearInterval(this.statusCheckInterval);
                    this.pdfPath = status.pdf;

                    // Show loading message
                    if (statusPDF) {
                        statusPDF.innerHTML = '<span class="spinner"></span> Loading PDF...';
                    }

                    // Load the real PDF
                    this.loadPdfPreview();

                    // After PDF loads, show ready
                    setTimeout(() => {
                        if (statusPDF) statusPDF.textContent = "✓ Ready";
                        this.showDownloadOption();
                    }, 500);
                }
            } catch (error) {
                console.error("Status check error:", error);
            }
        }, 200);
    }

    loadPdfPreview() {
        const previewSection = document.getElementById("previewSection");
        const pdfPreview = document.getElementById("pdfPreview");

        console.log("loadPdfPreview called, pdfPath:", this.pdfPath);
        if (!this.pdfPath) {
            console.log("No pdfPath, returning");
            return;
        }

        const url = `/api/download?path=${encodeURIComponent(this.pdfPath)}&preview=true`;
        console.log("Setting iframe src to:", url);
        pdfPreview.src = url;
        pdfPreview.style.display = "block";
        previewSection.style.display = "block";
        console.log("Preview section shown");
    }

    showDownloadOption() {
        const downloadSection = document.getElementById("downloadSection");
        const refreshSection = document.getElementById("refreshSection");
        console.log("showDownloadOption called, downloadSection:", downloadSection);
        if (downloadSection) {
            downloadSection.style.display = "block";
            console.log("Download section shown");
        }
        if (refreshSection) refreshSection.style.display = "none";
    }

    showRefreshOption() {
        const downloadSection = document.getElementById("downloadSection");
        const refreshSection = document.getElementById("refreshSection");
        if (downloadSection) downloadSection.style.display = "none";
        if (refreshSection) refreshSection.style.display = "block";
    }

    async checkStatus() {
        if (!this.statusPath) return;

        try {
            const response = await fetch(
                `/api/status?path=${encodeURIComponent(this.statusPath)}`
            );
            const status = await response.json();

            if (status.state === "success") {
                clearInterval(this.statusCheckInterval);
                this.pdfPath = status.pdf;
                document.getElementById("statusPDF").textContent = "✓ Ready";
                this.showDownloadOption();
                this.loadPdfPreview();
            }
        } catch (error) {
            console.error("Status check error:", error);
        }
    }

    download() {
        if (!this.pdfPath) return;

        const link = document.createElement("a");
        link.href = `/api/download?path=${encodeURIComponent(this.pdfPath)}`;
        link.download = "resume.pdf";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    async openGeneratedFolder() {
        if (!this.outputDir) return;

        try {
            const response = await fetch("/api/open-folder", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: this.outputDir }),
            });
            const data = await response.json();
            if (!data.success) {
                alert(`Could not open folder: ${data.error || "Unknown error"}`);
            }
        } catch (error) {
            console.error("Open folder error:", error);
            alert("Could not open the generated folder.");
        }
    }

    showError(message) {
        document.getElementById("errorMessage").textContent = message;
    }

    showState(state) {
        // Hide all states
        this.initialState.style.display = "none";
        this.loadingState.style.display = "none";
        this.successState.style.display = "none";
        this.errorState.style.display = "none";

        // Show selected state
        switch (state) {
            case "initial":
                this.initialState.style.display = "block";
                break;
            case "loading":
                this.loadingState.style.display = "block";
                break;
            case "success":
                this.successState.style.display = "block";
                break;
            case "error":
                this.errorState.style.display = "block";
                break;
        }
    }

    reset() {
        this.contentInput.value = "";
        this.companyNameInput.value = "";
        this.folderNameInput.value = "";
        this.validationDisplay.style.display = "none";
        this.generateBtn.disabled = true;
        this.showState("initial");
        this.statusPath = null;
        this.pdfPath = null;
        this.outputDir = null;
        clearInterval(this.statusCheckInterval);

        // Disable comparison mode
        document.querySelector(".app-content").classList.remove("comparison-mode");

        // Revoke object URLs to free memory
        const pdfPreview = document.getElementById("pdfPreview");
        if (pdfPreview.src) {
            URL.revokeObjectURL(pdfPreview.src);
            pdfPreview.src = "";
        }
    }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    new ResumeGenerator();
});
