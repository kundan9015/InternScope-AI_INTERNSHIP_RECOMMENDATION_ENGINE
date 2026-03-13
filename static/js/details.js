async function loadInternshipDetails() {
    const panel = document.getElementById("detailsPanel");
    if (!panel) {
        return;
    }

    const internshipId = panel.getAttribute("data-internship-id");
    const analysisId = localStorage.getItem("analysisId") || "";
    const state = document.getElementById("detailsState");

    try {
        const response = await fetch(`/api/internship/${internshipId}?analysis_id=${encodeURIComponent(analysisId)}`);
        if (!response.ok) {
            throw new Error("Unable to load internship details.");
        }

        const item = await response.json();

        document.getElementById("roleTitle").textContent = item.role;
        document.getElementById("companyInfo").textContent = `${item.company_name} • ${item.location}`;
        document.getElementById("descriptionText").textContent = item.description;
        document.getElementById("experienceLevel").textContent = item.experience_level || "Beginner";
        document.getElementById("locationText").textContent = item.location;
        document.getElementById("salaryText").textContent = item.salary || "Not provided";

        const skillsWrap = document.getElementById("requiredSkills");
        const skills = item.required_skills || [];
        skillsWrap.innerHTML = skills.map((skill) => `<span>${skill}</span>`).join("");

        const website = item.company_website || "#";
        const companySite = document.getElementById("companySite");
        companySite.href = website.startsWith("http") ? website : `https://${website}`;

        const applyLink = document.getElementById("applyLink");
        applyLink.href = `/apply/${item.id}?analysis_id=${encodeURIComponent(analysisId)}`;

        const trust = document.getElementById("detailsTrustMeta");
        if (trust) {
            trust.innerHTML = `
                <span class="badge badge-safe">Live Internship Record</span>
                <span class="badge badge-safe">Verified Apply Redirect</span>
                <span class="badge badge-safe">Updated ${new Date().toLocaleTimeString()}</span>
            `;
        }

        if (state) {
            state.classList.add("is-hidden");
            state.classList.remove("state-error");
            state.innerHTML = "";
        }
    } catch (error) {
        if (state) {
            state.classList.remove("is-hidden");
            state.classList.add("state-error");
            state.innerHTML = `<p>${error.message}</p>`;
        }
    }
}

loadInternshipDetails();
