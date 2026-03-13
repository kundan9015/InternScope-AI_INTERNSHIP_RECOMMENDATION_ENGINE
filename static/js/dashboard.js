const analysisId = localStorage.getItem("analysisId");
const aiFeatureLoaded = {
    career: false,
    success: false,
    feed: false,
    resume: false,
};

const dashboardState = {
    analysisData: null,
    recommendations: [],
};

function animateNumber(el, target, suffix = "") {
    if (!el || Number.isNaN(target)) {
        return;
    }

    const duration = 600;
    const start = performance.now();
    const from = 0;

    function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const value = from + (target - from) * progress;
        el.textContent = `${Math.round(value)}${suffix}`;
        if (progress < 1) {
            window.requestAnimationFrame(tick);
        }
    }

    window.requestAnimationFrame(tick);
}

async function loadDashboard() {
    if (!analysisId) {
        window.location.href = "/";
        return;
    }

    const response = await fetch(`/api/analysis/${analysisId}`);
    if (!response.ok) {
        return;
    }

    const data = await response.json();
    dashboardState.analysisData = data;

    const scoreEl = document.getElementById("resumeScore");
    if (scoreEl) {
        animateNumber(scoreEl, Number(data.resume_score || 0), "/100");
    }
    document.getElementById("candidateName").textContent = data.parsed_data.name || "Candidate";
    document.getElementById("candidateEmail").textContent = data.parsed_data.email || "Not found";
    const freshness = document.getElementById("dashboardFreshness");
    if (freshness) {
        freshness.textContent = `Live dashboard synced at ${new Date().toLocaleString()}`;
    }

    const skillsWrap = document.getElementById("skillsWrap");
    const skills = data.parsed_data.skills || [];
    skillsWrap.innerHTML = skills.length
        ? skills.map((skill) => `<span>${skill}</span>`).join("")
        : "<p>No skills extracted.</p>";

    const gapWrap = document.getElementById("gapWrap");
    const gaps = data.missing_skills || [];
    gapWrap.innerHTML = gaps.length
        ? gaps.slice(0, 15).map((skill) => `<span>${skill}</span>`).join("")
        : "<p>No major gaps detected.</p>";

    const suggestionsList = document.getElementById("suggestionsList");
    suggestionsList.innerHTML = (data.suggestions || [])
        .map((item) => `<li>${item}</li>`)
        .join("");

    document.getElementById("educationText").textContent = data.parsed_data.education || "Not mentioned";
    document.getElementById("projectsText").textContent = data.parsed_data.projects || "Not mentioned";
    document.getElementById("experienceText").textContent = data.parsed_data.experience || "Not mentioned";
    renderProfessionalLinks(data.parsed_data.links || {});

    const recResponse = await fetch(`/api/recommendations/${analysisId}`);
    const recPayload = recResponse.ok ? await recResponse.json() : { recommendations: [] };
    const recommendations = recPayload.recommendations || [];
    dashboardState.recommendations = recommendations;

    setTopMatch(recommendations);
    setProfileCompletion(data);

    renderScoreChart(data.score_breakdown || {});
}

function projectCountFromText(projectText) {
    if (!projectText || projectText === "Not mentioned") {
        return 0;
    }
    return projectText.split("\n").map((line) => line.trim()).filter(Boolean).length;
}

function setTopMatch(recommendations) {
    const top = recommendations[0];
    const roleEl = document.getElementById("topMatchRole");
    const companyEl = document.getElementById("topMatchCompany");
    const scoreEl = document.getElementById("topMatchScore");
    const applyEl = document.getElementById("topMatchApply");

    if (!roleEl || !companyEl || !scoreEl || !applyEl) {
        return;
    }

    if (!top) {
        roleEl.textContent = "No top match available yet";
        companyEl.textContent = "Run live recommendations to see best match.";
        scoreEl.textContent = "-";
        applyEl.removeAttribute("href");
        return;
    }

    roleEl.textContent = top.role || "Internship";
    companyEl.textContent = `${top.company_name || "Company"} • ${top.location || "Remote"}`;
    scoreEl.textContent = `Match ${(top.match_score || 0).toFixed(1)}% • Ranking ${(top.ranking_score || 0).toFixed(1)}%`;
    applyEl.href = `/apply/${top.id}?analysis_id=${encodeURIComponent(analysisId || "")}`;
}

function setProfileCompletion(data) {
    const completionEl = document.getElementById("profileCompletion");
    if (!completionEl) {
        return;
    }

    const parsed = data.parsed_data || {};
    let score = 0;
    if ((parsed.skills || []).length >= 4) score += 25;
    if (parsed.projects && parsed.projects !== "Not mentioned") score += 25;
    if (parsed.experience && parsed.experience !== "Not mentioned") score += 25;
    if (parsed.education && parsed.education !== "Not mentioned") score += 25;

    animateNumber(completionEl, score, "%");
}

function toSafeExternalUrl(url) {
    if (!url || typeof url !== "string") {
        return "";
    }
    const trimmed = url.trim();
    if (!trimmed) {
        return "";
    }
    if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
        return trimmed;
    }
    return `https://${trimmed}`;
}

function renderProfessionalLinks(links) {
    const target = document.getElementById("professionalLinks");
    if (!target) {
        return;
    }

    const entries = [
        { label: "LinkedIn", value: links.linkedin },
        { label: "GitHub", value: links.github },
        { label: "Portfolio", value: links.portfolio },
    ].filter((item) => item.value);

    if (!entries.length) {
        target.innerHTML = "<p class=\"muted-text\">No professional links found in resume.</p>";
        return;
    }

    target.innerHTML = entries
        .map((item) => {
            const href = toSafeExternalUrl(item.value);
            return `<a class="primary-link profile-link-item" href="${href}" target="_blank" rel="noopener">${item.label}</a>`;
        })
        .join("");
}

async function loadCareerPrediction(data) {
    const list = document.getElementById("careerPathsList");
    if (!list) {
        return;
    }

    try {
        const payload = {
            skills: data.parsed_data.skills || [],
            projects: data.parsed_data.projects || "",
            education: data.parsed_data.education || "",
            experience: data.parsed_data.experience || "",
            experience_years: data.parsed_data.experience_years || 0,
        };

        const response = await fetch("/predict-career", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || "Unable to predict career paths.");
        }

        const paths = result.career_paths || [];
        const topCareerPath = document.getElementById("topCareerPath");
        if (topCareerPath) {
            topCareerPath.textContent = paths.length ? `${paths[0].role} (${(paths[0].score * 100).toFixed(1)}%)` : "Not available";
        }
        list.innerHTML = paths.length
            ? paths.map((item) => `<li>${item.role}: ${(item.score * 100).toFixed(1)}%</li>`).join("")
            : "<li>No paths predicted.</li>";
    } catch (error) {
        list.innerHTML = `<li>${error.message}</li>`;
    }
}

async function loadSuccessPrediction(data, recommendations) {
    const successText = document.getElementById("successProbabilityText");
    const contextText = document.getElementById("successContext");

    if (!successText || !contextText) {
        return;
    }

    try {
        const firstRec = (recommendations || [])[0];

        if (!firstRec) {
            successText.textContent = "No recommendation available for prediction yet.";
            contextText.textContent = "Upload resume and fetch recommendations first.";
            return;
        }

        const payload = {
            internship: firstRec.role,
            user_skills: data.parsed_data.skills || [],
            required_skills: firstRec.required_skills || [],
            resume_score: data.resume_score || 0,
            num_projects: projectCountFromText(data.parsed_data.projects || ""),
            experience_years: data.parsed_data.experience_years || 0,
        };

        const response = await fetch("/predict-success", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Unable to compute success probability.");
        }

        successText.textContent = `Selection Probability: ${(result.success_probability * 100).toFixed(1)}%`;
        contextText.textContent = `Based on role: ${result.internship}`;
    } catch (error) {
        successText.textContent = error.message;
        contextText.textContent = "";
    }
}

async function loadPersonalizedFeed() {
    const list = document.getElementById("personalizedFeedList");
    if (!list) {
        return;
    }

    try {
        const response = await fetch(`/personalized-feed?analysis_id=${encodeURIComponent(analysisId)}&interests=ai,ml,data`);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Unable to load personalized feed.");
        }

        const rows = result.recommendations || [];
        list.innerHTML = rows.length
            ? rows.slice(0, 5).map((item) => `<li>${item.role} at ${item.company_name || item.company} (${(item.match_score * 100).toFixed(1)}%)</li>`).join("")
            : "<li>No personalized recommendations available.</li>";
    } catch (error) {
        list.innerHTML = `<li>${error.message}</li>`;
    }
}

async function loadResumeAnalyzer() {
    const weakPointsList = document.getElementById("resumeWeakPoints");
    const suggestionsList = document.getElementById("resumeSuggestions");

    if (!weakPointsList || !suggestionsList) {
        return;
    }

    try {
        const response = await fetch("/resume-analysis", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ analysis_id: analysisId }),
        });
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Unable to run resume analyzer.");
        }

        weakPointsList.innerHTML = (result.weak_points || []).length
            ? (result.weak_points || []).map((item) => `<li>${item}</li>`).join("")
            : "<li>No major weak points detected.</li>";

        suggestionsList.innerHTML = (result.suggestions || []).length
            ? (result.suggestions || []).map((item) => `<li>${item}</li>`).join("")
            : "<li>No suggestions available.</li>";
    } catch (error) {
        weakPointsList.innerHTML = `<li>${error.message}</li>`;
        suggestionsList.innerHTML = "<li>-</li>";
    }
}

function renderScoreChart(breakdown) {
    const chartEl = document.getElementById("scoreChart");
    if (!chartEl) {
        return;
    }

    new Chart(chartEl, {
        type: "bar",
        data: {
            labels: ["Skills", "Projects", "Education", "Experience"],
            datasets: [
                {
                    label: "Score Contribution",
                    data: [
                        breakdown.skills_match || 0,
                        breakdown.projects || 0,
                        breakdown.education || 0,
                        breakdown.experience || 0,
                    ],
                    backgroundColor: ["#2b7a78", "#e06c36", "#4e8aab", "#b94f22"],
                    borderRadius: 8,
                },
            ],
        },
        options: {
            plugins: {
                legend: { display: false },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 50,
                },
            },
        },
    });
}

function setAiHint(message) {
    const hintEl = document.getElementById("aiFeatureHint");
    if (hintEl) {
        hintEl.textContent = message;
    }
}

function openAiInsightsPanel() {
    const content = document.getElementById("aiInsightsContent");
    const toggleBtn = document.getElementById("aiInsightsToggle");
    if (!content || !toggleBtn) {
        return;
    }

    const isHidden = content.classList.contains("is-hidden");
    if (isHidden) {
        content.classList.remove("is-hidden");
        content.setAttribute("aria-hidden", "false");
        toggleBtn.textContent = "Hide AI Insights";
        toggleBtn.setAttribute("aria-expanded", "true");
    }
}

function initAiInsightsToggle() {
    const content = document.getElementById("aiInsightsContent");
    const toggleBtn = document.getElementById("aiInsightsToggle");
    if (!content || !toggleBtn) {
        return;
    }

    toggleBtn.addEventListener("click", () => {
        const shouldShow = content.classList.contains("is-hidden");
        content.classList.toggle("is-hidden", !shouldShow);
        content.setAttribute("aria-hidden", shouldShow ? "false" : "true");
        toggleBtn.textContent = shouldShow ? "Hide AI Insights" : "Open AI Insights";
        toggleBtn.setAttribute("aria-expanded", shouldShow ? "true" : "false");
    });
}

function activateFeatureButton(activeFeature) {
    document.querySelectorAll(".ai-feature-btn").forEach((btn) => {
        const isActive = btn.dataset.feature === activeFeature;
        btn.classList.toggle("active", isActive);
        btn.setAttribute("aria-selected", isActive ? "true" : "false");
    });
}

function showSelectedFeaturePanel(panelId) {
    document.querySelectorAll(".ai-feature-panel").forEach((panel) => {
        const isSelected = panel.id === panelId;
        panel.classList.toggle("is-hidden", !isSelected);
        panel.setAttribute("aria-hidden", isSelected ? "false" : "true");
    });
}

async function onFeatureButtonClick(feature, panelId) {
    openAiInsightsPanel();
    activateFeatureButton(feature);
    showSelectedFeaturePanel(panelId);

    if (!dashboardState.analysisData) {
        setAiHint("Please wait for the dashboard to finish loading before running insights.");
        return;
    }

    if (aiFeatureLoaded[feature]) {
        setAiHint("This insight is already loaded. Click another feature to continue.");
        return;
    }

    setAiHint("Running selected AI insight...");

    try {
        if (feature === "career") {
            await loadCareerPrediction(dashboardState.analysisData);
        } else if (feature === "success") {
            await loadSuccessPrediction(dashboardState.analysisData, dashboardState.recommendations);
        } else if (feature === "feed") {
            await loadPersonalizedFeed();
        } else if (feature === "resume") {
            await loadResumeAnalyzer();
        }

        aiFeatureLoaded[feature] = true;
        setAiHint("Insight loaded successfully. Choose another feature for more results.");
    } catch (error) {
        setAiHint(error.message || "Unable to load this insight right now.");
    }
}

function initAiFeatureButtons() {
    const buttons = document.querySelectorAll(".ai-feature-btn");
    buttons.forEach((btn) => {
        btn.addEventListener("click", () => {
            onFeatureButtonClick(btn.dataset.feature, btn.dataset.panel);
        });
    });
}

const recommendationsLink = document.getElementById("viewRecommendationsLink");
if (recommendationsLink && analysisId) {
    recommendationsLink.href = `/matched-internships?analysis_id=${encodeURIComponent(analysisId)}`;
}

initAiInsightsToggle();
initAiFeatureButtons();
loadDashboard();
