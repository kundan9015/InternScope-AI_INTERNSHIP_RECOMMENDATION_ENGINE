const params = new URLSearchParams(window.location.search);
const queryAnalysisId = params.get("analysis_id");
const analysisId = queryAnalysisId || localStorage.getItem("analysisId");

if (analysisId) {
    localStorage.setItem("analysisId", analysisId);
}

function confidenceLabel(score) {
    if (score >= 75) return "High Confidence";
    if (score >= 50) return "Medium Confidence";
    return "Early Match";
}

function formatTimestamp() {
    return new Date().toLocaleString();
}

function setRecommendationMeta(count) {
    const meta = document.getElementById("recommendationMeta");
    if (!meta) return;
    meta.textContent = `${count} roles loaded • Live sync at ${formatTimestamp()}`;
}

function setStateMessage(message, isError = false) {
    const state = document.getElementById("recommendationState");
    if (!state) return;
    state.classList.remove("is-hidden");
    state.classList.toggle("state-error", isError);
    state.innerHTML = `<p>${message}</p>${isError ? '<button id="retryRecommendationBtn" type="button">Retry</button>' : ""}`;

    const retryBtn = document.getElementById("retryRecommendationBtn");
    if (retryBtn) {
        retryBtn.addEventListener("click", () => loadLiveRecommendations());
    }
}

function clearStateMessage() {
    const state = document.getElementById("recommendationState");
    if (!state) return;
    state.classList.add("is-hidden");
    state.classList.remove("state-error");
    state.innerHTML = "";
}

function renderSkeletonCards() {
    const list = document.getElementById("recommendationList");
    if (!list) return;
    clearStateMessage();
    list.innerHTML = Array.from({ length: 4 })
        .map(
            () => `
            <article class="reco-card skeleton-card">
                <div class="skeleton-line w60"></div>
                <div class="skeleton-line w40"></div>
                <div class="skeleton-line w100"></div>
                <div class="skeleton-line w90"></div>
                <div class="skeleton-line w70"></div>
            </article>
        `,
        )
        .join("");
}

function updateStickyCta(recommendations) {
    const cta = document.getElementById("mobileStickyCta");
    if (!cta || !recommendations.length) return;
    const top = recommendations[0];
    cta.href = `/apply/${top.id}?analysis_id=${encodeURIComponent(analysisId || "")}`;
    cta.textContent = `Apply: ${top.role}`;
}

function renderCards(listEl, recommendations, emptyMessage) {
    if (!recommendations.length) {
        listEl.innerHTML = "";
        setRecommendationMeta(0);
        setStateMessage(emptyMessage, false);
        return;
    }

    clearStateMessage();
    setRecommendationMeta(recommendations.length);
    updateStickyCta(recommendations);

    listEl.innerHTML = recommendations
        .map((item) => {
            const fakeInfo = item.fake_detection || { label: "low-risk", risk_score: 0 };
            const riskBadgeClass = fakeInfo.label === "suspicious" ? "badge-risk" : "badge-safe";
            const sourceLabel = item.source || "cached";
            const confidence = confidenceLabel(Number(item.ranking_score || 0));
            const matched = (item.matched_skills || []).slice(0, 4);
            const explainability = matched.length
                ? matched.map((skill) => `<span class="badge badge-safe">${skill}</span>`).join("")
                : '<span class="badge badge-risk">Skill overlap is currently low</span>';

            return `
                <article class="reco-card">
                    <h3>${item.role}</h3>
                    <p><strong>${item.company_name}</strong> • ${item.location}</p>
                    <p>${(item.description || "").slice(0, 180)}...</p>
                    <div class="meta">
                        <span>Match: ${item.match_score}%</span>
                        <span>Ranking: ${item.ranking_score}%</span>
                        <span class="badge ${riskBadgeClass}">Risk: ${fakeInfo.risk_score}%</span>
                        <span class="badge badge-safe">Source: ${sourceLabel}</span>
                        <span class="badge badge-safe">${confidence}</span>
                    </div>
                    <div class="explain-row">
                        <span class="meta-label">Matched because:</span>
                        ${explainability}
                    </div>
                    <div class="meta" style="margin-top: 10px;">
                        <a class="primary-link" href="/internship/${item.id}">View details</a>
                        <a class="primary-link" href="/apply/${item.id}?analysis_id=${encodeURIComponent(analysisId || "")}" target="_blank" rel="noopener">Apply</a>
                    </div>
                </article>
            `;
        })
        .join("");
}

async function loadRecommendations() {
    if (!analysisId) {
        window.location.href = "/";
        return;
    }

    const response = await fetch(`/api/recommendations/${analysisId}`);
    if (!response.ok) {
        setStateMessage("Unable to load recommendations. Please refresh.", true);
        return;
    }

    const list = document.getElementById("recommendationList");
    const payload = await response.json();
    renderCards(list, payload.recommendations || [], "No suggested internships available right now.");
}

async function loadLiveRecommendations() {
    if (!analysisId) {
        return;
    }

    const liveStatus = document.getElementById("liveStatus");
    const list = document.getElementById("recommendationList");
    const liveSearch = document.getElementById("liveSearch");
    const query = (liveSearch?.value || "").trim();

    liveStatus.textContent = "Fetching latest internships...";
    renderSkeletonCards();

    try {
        const url = query
            ? `/api/recommendations/live/${analysisId}?q=${encodeURIComponent(query)}`
            : `/api/recommendations/live/${analysisId}`;
        const response = await fetch(url);
        const payload = await response.json();

        if (!response.ok) {
            throw new Error(payload.error || "Failed to fetch live internships.");
        }

        renderCards(list, payload.recommendations || [], "No live internships found for this query.");
        liveStatus.textContent = "Suggested internships updated.";
    } catch (error) {
        liveStatus.textContent = error.message;
        list.innerHTML = "";
        setStateMessage("We could not fetch live internships right now. Please try again.", true);
    }
}

const liveBtn = document.getElementById("liveFetchBtn");
if (liveBtn) {
    liveBtn.addEventListener("click", loadLiveRecommendations);
}

document.getElementById("resetSearchBtn")?.addEventListener("click", async () => {
    const liveSearch = document.getElementById("liveSearch");
    if (liveSearch) {
        liveSearch.value = "";
    }
    await loadRecommendations();
});

async function initRecommendationsPage() {
    if (params.get("auto_live") === "1") {
        await loadLiveRecommendations();
        return;
    }

    await loadRecommendations();
    if (document.getElementById("recommendationList").children.length === 0) {
        await loadLiveRecommendations();
    }
}

initRecommendationsPage();
