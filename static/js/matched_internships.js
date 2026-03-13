const params = new URLSearchParams(window.location.search);
const analysisId = params.get("analysis_id") || localStorage.getItem("analysisId");

if (analysisId) {
    localStorage.setItem("analysisId", analysisId);
}

function formatTimestamp() {
    return new Date().toLocaleString();
}

function setMatchedMeta(count) {
    const meta = document.getElementById("matchedMeta");
    if (!meta) return;
    meta.textContent = `${count} matched roles • Updated ${formatTimestamp()}`;
}

function setMatchedState(message, isError = false) {
    const state = document.getElementById("matchedState");
    if (!state) return;
    state.classList.remove("is-hidden");
    state.classList.toggle("state-error", isError);
    state.innerHTML = `<p>${message}</p>${isError ? '<button id="retryMatchedBtn" type="button">Retry</button>' : ""}`;

    const retryBtn = document.getElementById("retryMatchedBtn");
    if (retryBtn) {
        retryBtn.addEventListener("click", () => fetchMatchedInternships());
    }
}

function clearMatchedState() {
    const state = document.getElementById("matchedState");
    if (!state) return;
    state.classList.add("is-hidden");
    state.classList.remove("state-error");
    state.innerHTML = "";
}

function updateStickyMatchCta(recommendations) {
    const cta = document.getElementById("mobileStickyMatchCta");
    if (!cta || !recommendations.length) return;
    const top = recommendations[0];
    cta.href = `/internship/${top.id}`;
    cta.textContent = `Top Match: ${top.role}`;
}

function renderMatchedSkeleton() {
    const list = document.getElementById("matchedList");
    if (!list) return;
    clearMatchedState();
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

function renderMatchedCards(recommendations) {
    const list = document.getElementById("matchedList");
    if (!recommendations.length) {
        list.innerHTML = "";
        setMatchedMeta(0);
        setMatchedState("No internships matched right now. Try manual search.", false);
        return;
    }

    clearMatchedState();
    setMatchedMeta(recommendations.length);
    updateStickyMatchCta(recommendations);

    list.innerHTML = recommendations
        .map((item) => {
            const fakeInfo = item.fake_detection || { label: "low-risk", risk_score: 0 };
            const riskBadgeClass = fakeInfo.label === "suspicious" ? "badge-risk" : "badge-safe";
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

async function fetchMatchedInternships(customQuery = "") {
    const status = document.getElementById("matchedStatus");

    if (!analysisId) {
        window.location.href = "/";
        return;
    }

    status.textContent = "Fetching internships matched to your resume...";
    renderMatchedSkeleton();

    try {
        const url = customQuery.trim()
            ? `/api/recommendations/matched/${analysisId}?q=${encodeURIComponent(customQuery.trim())}`
            : `/api/recommendations/matched/${analysisId}`;

        const response = await fetch(url);
        const payload = await response.json();

        if (!response.ok) {
            throw new Error(payload.error || "Unable to load matched internships.");
        }

        renderMatchedCards(payload.recommendations || []);
        status.textContent = "Matched internships loaded.";
    } catch (error) {
        status.textContent = error.message;
        document.getElementById("matchedList").innerHTML = "";
        setMatchedState("Could not load internships right now. Please retry.", true);
    }
}

document.getElementById("manualSearchBtn")?.addEventListener("click", () => {
    const manualSearch = document.getElementById("manualSearch");
    fetchMatchedInternships(manualSearch?.value || "");
});

document.getElementById("clearSearchBtn")?.addEventListener("click", () => {
    const manualSearch = document.getElementById("manualSearch");
    if (manualSearch) {
        manualSearch.value = "";
    }
    fetchMatchedInternships();
});

fetchMatchedInternships();
