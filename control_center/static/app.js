const state = {
  page: "dashboard",
  missions: [],
  selectedMissionId: null,
};

const pageTitles = {
  dashboard: "Dashboard",
  missions: "Missions",
  "mission-detail": "Mission Detail",
  "source-review": "Source Review",
  coverage: "Coverage",
  "knowledge-debt": "Knowledge Debt",
  logs: "Logs / Audit Trail",
  settings: "Settings",
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error || "Request failed");
  }
  return body;
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function showNotice(message) {
  const notice = document.querySelector("#notice");
  notice.textContent = message;
  notice.classList.remove("hidden");
  window.setTimeout(() => notice.classList.add("hidden"), 3200);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function badge(value) {
  const normalized = String(value || "").toLowerCase();
  let cls = "";
  if (["approved", "published", "resolved", "complete"].includes(normalized)) cls = "good";
  if (["created", "candidate_found", "pending_review", "needs_review", "open", "high"].includes(normalized)) cls = "warn";
  if (["rejected", "blocked", "critical", "cancelled"].includes(normalized)) cls = "bad";
  return `<span class="badge ${cls}">${escapeHtml(value)}</span>`;
}

function item(title, body, actions = "") {
  return `<div class="item"><h4>${escapeHtml(title)}</h4>${body}${actions ? `<div class="item-actions">${actions}</div>` : ""}</div>`;
}

function setPage(page) {
  state.page = page;
  document.querySelectorAll("nav button").forEach((button) => {
    button.classList.toggle("active", button.dataset.page === page);
  });
  document.querySelectorAll(".page").forEach((section) => {
    section.classList.toggle("active", section.id === `page-${page}`);
  });
  document.querySelector("#page-title").textContent = pageTitles[page] || page;
  refresh();
}

async function refresh() {
  await loadMissions();
  if (state.page === "dashboard") return loadDashboard();
  if (state.page === "missions") return renderMissions();
  if (state.page === "mission-detail") return renderMissionDetail();
  if (state.page === "source-review") return renderSourceReview();
  if (state.page === "coverage") return renderCoverage();
  if (state.page === "knowledge-debt") return renderDebt();
  if (state.page === "logs") return renderLogs();
  if (state.page === "settings") return renderSettings();
}

async function loadMissions() {
  state.missions = await api("/api/missions");
  if (!state.selectedMissionId && state.missions.length) {
    state.selectedMissionId = state.missions[0].id;
  }
  fillMissionSelects();
}

function fillMissionSelects() {
  const options = [
    `<option value="">No mission</option>`,
    ...state.missions.map((mission) => `<option value="${escapeHtml(mission.id)}">${escapeHtml(mission.name)}</option>`),
  ].join("");
  ["mission-selector", "source-mission-select", "log-mission-select"].forEach((id) => {
    const select = document.querySelector(`#${id}`);
    if (!select) return;
    const prior = select.value || state.selectedMissionId || "";
    select.innerHTML = options;
    select.value = prior;
  });
}

async function loadDashboard() {
  const data = await api("/api/dashboard");
  const cards = document.querySelector("#dashboard-cards");
  cards.innerHTML = Object.entries(data.counts)
    .map(([key, value]) => `<div class="card"><span class="meta">${escapeHtml(key.replaceAll("_", " "))}</span><strong>${value}</strong></div>`)
    .join("");

  document.querySelector("#cko-recommendations").innerHTML =
    data.cko_recommendations.map((log) => item(log.agent_name, `<p>${escapeHtml(log.message)}</p><p class="meta">${escapeHtml(log.created_at)}</p>`)).join("") ||
    `<p class="muted">No CKO recommendations yet.</p>`;

  document.querySelector("#recent-events").innerHTML =
    data.recent_events.map((event) => item(event.event_type, `<p>${escapeHtml(event.summary)}</p><p class="meta">${escapeHtml(event.created_at)} by ${escapeHtml(event.actor)}</p>`)).join("") ||
    `<p class="muted">No mission events yet.</p>`;
}

function renderMissions() {
  const list = document.querySelector("#missions-list");
  list.innerHTML =
    state.missions
      .map((mission) =>
        item(
          mission.name,
          `
          <p>${badge(mission.status)} ${badge(mission.priority)}</p>
          <p class="meta">${escapeHtml(mission.target_pack)}</p>
          <p>${escapeHtml(mission.coverage_goal || "No coverage goal set")}</p>
          `,
          `<button data-open-mission="${escapeHtml(mission.id)}">Open</button>`
        )
      )
      .join("") || `<p class="muted">No missions yet.</p>`;
}

async function renderMissionDetail() {
  const selector = document.querySelector("#mission-selector");
  if (selector.value) state.selectedMissionId = selector.value;
  const detail = document.querySelector("#mission-detail");
  if (!state.selectedMissionId) {
    detail.innerHTML = `<p class="muted">No mission selected.</p>`;
    return;
  }
  const mission = await api(`/api/missions/${state.selectedMissionId}`);
  const events = await api(`/api/mission_events?mission_id=${encodeURIComponent(state.selectedMissionId)}`);
  detail.innerHTML = `
    <div class="grid two">
      <div>
        ${item(mission.name, `
          <p>${badge(mission.status)} ${badge(mission.priority)}</p>
          <p><strong>Target Pack:</strong> ${escapeHtml(mission.target_pack)}</p>
          <p><strong>Reviewer:</strong> ${escapeHtml(mission.human_reviewer || "Unassigned")}</p>
          <p><strong>Coverage Goal:</strong> ${escapeHtml(mission.coverage_goal || "None")}</p>
          <p><strong>Approved Domains:</strong> ${escapeHtml(mission.approved_domains || "None")}</p>
          <p><strong>Safety:</strong> ${escapeHtml(mission.safety_requirements || "None")}</p>
          <p><strong>CKO:</strong> ${escapeHtml(mission.cko_recommendation || "No recommendation")}</p>
        `)}
        <form id="mission-status-form" class="inline-form">
          <select name="status">
            ${["created","awaiting_approval","approved","research","source_vetting","acquisition","ocr","knowledge_engineering","indexing","validation","compilation","human_review","published","blocked","paused","cancelled"]
              .map((status) => `<option ${status === mission.status ? "selected" : ""}>${status}</option>`).join("")}
          </select>
          <input name="reason" placeholder="Human decision reason" />
          <button>Update Status</button>
        </form>
      </div>
      <div>
        <h3>Mission Events</h3>
        <div class="stack">
          ${events.map((event) => item(event.event_type, `<p>${escapeHtml(event.summary)}</p><p class="meta">${escapeHtml(event.created_at)} by ${escapeHtml(event.actor)}</p>`)).join("") || `<p class="muted">No events yet.</p>`}
        </div>
      </div>
    </div>
  `;
}

async function renderSourceReview() {
  const sources = await api("/api/source_candidates");
  document.querySelector("#sources-list").innerHTML =
    sources
      .map((source) =>
        item(
          source.title,
          `
          <p>${badge(source.status)} ${badge(source.license_status)} ${badge(source.source_class)}</p>
          <p class="meta">${escapeHtml(source.url_or_path)}</p>
          <p><strong>Quality:</strong> ${Number(source.quality_score).toFixed(2)} | <strong>Type:</strong> ${escapeHtml(source.source_type)}</p>
          <p>${escapeHtml(source.relevance_notes || "")}</p>
          `,
          source.status === "approved" || source.status === "rejected"
            ? ""
            : `
              <button data-review-source="${escapeHtml(source.id)}" data-decision="approved">Approve</button>
              <button class="danger" data-review-source="${escapeHtml(source.id)}" data-decision="rejected">Reject</button>
            `
        )
      )
      .join("") || `<p class="muted">No source candidates yet.</p>`;
}

async function renderCoverage() {
  const items = await api("/api/coverage_items");
  document.querySelector("#coverage-list").innerHTML =
    items
      .map((entry) => {
        const current = Math.max(0, Math.min(100, Number(entry.current_percent)));
        return item(
          entry.name,
          `
          <p>${badge(entry.status)} <span class="meta">${escapeHtml(entry.pack_id)}</span></p>
          <div class="progress"><span style="width:${current}%"></span></div>
          <p><strong>${current}%</strong> current / ${Number(entry.target_percent)}% target</p>
          <p class="meta">${escapeHtml(entry.notes || "")}</p>
          `,
          `<button data-coverage-inc="${escapeHtml(entry.id)}">+5%</button>`
        );
      })
      .join("") || `<p class="muted">No coverage items yet.</p>`;
}

async function renderDebt() {
  const items = await api("/api/knowledge_debt");
  document.querySelector("#debt-list").innerHTML =
    items
      .map((debt) =>
        item(
          debt.debt_type,
          `
          <p>${badge(debt.status)} ${badge(debt.severity)}</p>
          <p>${escapeHtml(debt.description)}</p>
          <p class="meta">${escapeHtml(debt.recommended_action || "")}</p>
          `,
          debt.status === "resolved" ? "" : `<button data-resolve-debt="${escapeHtml(debt.id)}">Resolve</button>`
        )
      )
      .join("") || `<p class="muted">No Knowledge Debt items yet.</p>`;
}

async function renderLogs() {
  const [events, logs, approvals] = await Promise.all([
    api("/api/mission_events"),
    api("/api/agent_logs"),
    api("/api/approvals"),
  ]);
  document.querySelector("#audit-list").innerHTML =
    [...events.map((event) => ({ ...event, kind: "event" })), ...approvals.map((approval) => ({ ...approval, kind: "approval" }))]
      .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
      .slice(0, 100)
      .map((record) => {
        if (record.kind === "approval") {
          return item(`approval: ${record.decision}`, `<p>${escapeHtml(record.target_type)} ${escapeHtml(record.target_id)}</p><p>${escapeHtml(record.reason || "")}</p><p class="meta">${escapeHtml(record.created_at)} by ${escapeHtml(record.approver)}</p>`);
        }
        return item(record.event_type, `<p>${escapeHtml(record.summary)}</p><p class="meta">${escapeHtml(record.created_at)} by ${escapeHtml(record.actor)}</p>`);
      })
      .join("") || `<p class="muted">No audit records yet.</p>`;

  document.querySelector("#agent-logs-list").innerHTML =
    logs.map((log) => item(`${log.agent_name}: ${log.log_type}`, `<p>${escapeHtml(log.message)}</p><p class="meta">${escapeHtml(log.created_at)}</p>`)).join("") ||
    `<p class="muted">No logs yet.</p>`;
}

async function renderSettings() {
  const settings = await api("/api/settings");
  document.querySelector("#settings-detail").innerHTML = `
    ${item("Runtime", `
      <p><strong>Database:</strong> ${escapeHtml(settings.database_path)}</p>
      <p><strong>Module Root:</strong> ${escapeHtml(settings.module_root)}</p>
    `)}
    ${item("Guardrails", `
      <p>${badge(`autonomous crawling: ${settings.autonomous_crawling}`)}</p>
      <p>${badge(`autonomous publishing: ${settings.autonomous_publishing}`)}</p>
      <p>${badge(`pack compilation: ${settings.expert_pack_compilation}`)}</p>
      <p>${badge(`human approval required: ${settings.human_approval_required}`)}</p>
    `)}
  `;
}

function bindForms() {
  document.querySelector("#mission-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const mission = await api("/api/missions", { method: "POST", body: JSON.stringify(formData(event.target)) });
    state.selectedMissionId = mission.id;
    event.target.reset();
    showNotice("Mission created.");
    await refresh();
  });

  document.querySelector("#source-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await api("/api/source_candidates", { method: "POST", body: JSON.stringify(formData(event.target)) });
    event.target.reset();
    showNotice("Source candidate added.");
    await refresh();
  });

  document.querySelector("#coverage-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await api("/api/coverage_items", { method: "POST", body: JSON.stringify(formData(event.target)) });
    event.target.reset();
    showNotice("Coverage item added.");
    await refresh();
  });

  document.querySelector("#debt-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await api("/api/knowledge_debt", { method: "POST", body: JSON.stringify(formData(event.target)) });
    event.target.reset();
    showNotice("Knowledge Debt item added.");
    await refresh();
  });

  document.querySelector("#log-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await api("/api/agent_logs", { method: "POST", body: JSON.stringify(formData(event.target)) });
    event.target.reset();
    showNotice("Log added.");
    await refresh();
  });

  document.querySelector("#cko-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = formData(event.target);
    await api("/api/agent_logs", {
      method: "POST",
      body: JSON.stringify({ agent_name: "CKO", log_type: "cko_recommendation", message: data.message }),
    });
    event.target.reset();
    showNotice("CKO recommendation added.");
    await refresh();
  });
}

function bindClicks() {
  document.querySelector("#nav").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-page]");
    if (button) setPage(button.dataset.page);
  });

  document.querySelector("#refresh-button").addEventListener("click", refresh);

  document.body.addEventListener("click", async (event) => {
    const openMission = event.target.closest("[data-open-mission]");
    if (openMission) {
      state.selectedMissionId = openMission.dataset.openMission;
      document.querySelector("#mission-selector").value = state.selectedMissionId;
      setPage("mission-detail");
      return;
    }

    const review = event.target.closest("[data-review-source]");
    if (review) {
      const decision = review.dataset.decision;
      const reason = window.prompt(`Reason for source ${decision}?`, decision === "approved" ? "Human approved source for MVP intake." : "Human rejected source.");
      if (reason === null) return;
      await api(`/api/source_candidates/${review.dataset.reviewSource}/review`, {
        method: "POST",
        body: JSON.stringify({ decision, notes: reason, reviewer: "human" }),
      });
      showNotice(`Source ${decision}.`);
      await refresh();
      return;
    }

    const coverageInc = event.target.closest("[data-coverage-inc]");
    if (coverageInc) {
      const items = await api("/api/coverage_items");
      const current = items.find((entry) => entry.id === coverageInc.dataset.coverageInc);
      if (!current) return;
      await api(`/api/coverage_items/${coverageInc.dataset.coverageInc}`, {
        method: "PATCH",
        body: JSON.stringify({ current_percent: Math.min(100, Number(current.current_percent) + 5) }),
      });
      await refresh();
      return;
    }

    const resolveDebt = event.target.closest("[data-resolve-debt]");
    if (resolveDebt) {
      await api(`/api/knowledge_debt/${resolveDebt.dataset.resolveDebt}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "resolved" }),
      });
      showNotice("Knowledge Debt resolved.");
      await refresh();
    }
  });

  document.body.addEventListener("submit", async (event) => {
    if (event.target.id !== "mission-status-form") return;
    event.preventDefault();
    const data = formData(event.target);
    await api(`/api/missions/${state.selectedMissionId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
    showNotice("Mission status updated.");
    await refresh();
  });

  document.querySelector("#mission-selector").addEventListener("change", (event) => {
    state.selectedMissionId = event.target.value;
    renderMissionDetail();
  });
}

async function boot() {
  bindForms();
  bindClicks();
  await refresh();
}

boot().catch((error) => {
  console.error(error);
  showNotice(error.message);
});
