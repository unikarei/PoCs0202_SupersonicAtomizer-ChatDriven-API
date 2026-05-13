let activeProjectId = null;
let activeCaseId = null;
let latestPlanId = null;
let latestRunId = null;
let latestPlanStatus = null;
let activeProjectTree = null;
let activeThreadId = null;
let activeProjectSolverUrl = null;
let reportPage = 1;
const reportPageSize = 5;
let currentReportPage = [];
let compareModeEnabled = false;
let compareViewMode = "overlay";
const selectedCompareReportIds = new Set();

const plotConfig = [
  { title: "Area Profile", key: "A", yLabel: "Area profile (m²)" },
  { title: "Pressure", key: "pressure", yLabel: "Pressure (Pa)" },
  { title: "Temperature", key: "temperature", yLabel: "Temperature (K)" },
  { title: "Working-fluid velocity", key: "working_fluid_velocity", yLabel: "Working-fluid velocity (m/s)" },
  { title: "Droplet velocity", key: "droplet_velocity", yLabel: "Droplet velocity (m/s)" },
  { title: "Slip velocity", key: "slip_velocity", yLabel: "Slip velocity (m/s)" },
  { title: "Mach number", key: "Mach_number", yLabel: "Mach number (-)" },
  { title: "Droplet mean diameter", key: "droplet_mean_diameter", yLabel: "Droplet mean diameter (um)", scale: 1e6 },
  { title: "Droplet maximum diameter", key: "droplet_maximum_diameter", yLabel: "Droplet maximum diameter (um)", scale: 1e6 },
  { title: "Weber number", key: "Weber_number", yLabel: "Weber number (-)" },
  { title: "Pressure / Inlet total pressure", key: "pressure_over_total", yLabel: "Pressure / Inlet total pressure (-)" },
];

const $ = (id) => document.getElementById(id);

function log(message, kind = "info") {
  const logEl = $("chat-log");
  const item = document.createElement("div");
  item.className = "chat-item";
  const now = new Date().toLocaleTimeString();
  item.innerHTML = `<small>${now} · ${kind}</small><div>${escapeHtml(message)}</div>`;
  logEl.prepend(item);
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = payload && payload.detail ? payload.detail : text || response.statusText;
    throw new Error(detail);
  }
  return payload;
}

function setTabs(tabName) {
  document.querySelectorAll(".tab-btn").forEach((button) => button.classList.toggle("active", button.dataset.tab === tabName));
  document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));
  $("tab-" + tabName).classList.add("active");
}

function initPaneResizer() {
  const shell = document.querySelector(".app-shell");
  const chatPane = document.querySelector(".chat");
  const resizer = $("workspace-chat-resizer");
  if (!shell || !chatPane || !resizer) return;

  const minChatWidth = 280;
  const minWorkspaceWidth = 520;
  const minExplorerWidth = 300;
  let isDragging = false;
  let startX = 0;
  let startWidth = 0;

  const updateChatWidth = (clientX) => {
    const shellStyle = window.getComputedStyle(shell);
    const gap = parseFloat(shellStyle.columnGap || shellStyle.gap || "12") || 12;
    const resizerWidth = parseFloat(
      window.getComputedStyle(document.documentElement).getPropertyValue("--resizer-width")
    ) || 10;

    const maxChatWidth = Math.max(
      minChatWidth,
      shell.clientWidth - minExplorerWidth - minWorkspaceWidth - resizerWidth - gap * 3
    );
    const delta = clientX - startX;
    const nextWidth = Math.max(minChatWidth, Math.min(maxChatWidth, startWidth - delta));
    document.documentElement.style.setProperty("--chat-width", `${nextWidth}px`);
  };

  resizer.addEventListener("pointerdown", (event) => {
    if (window.matchMedia("(max-width: 1180px)").matches) return;
    isDragging = true;
    startX = event.clientX;
    startWidth = chatPane.getBoundingClientRect().width;
    resizer.setPointerCapture(event.pointerId);
    document.body.classList.add("is-resizing");
  });

  resizer.addEventListener("pointermove", (event) => {
    if (!isDragging) return;
    updateChatWidth(event.clientX);
  });

  const stopDragging = () => {
    if (!isDragging) return;
    isDragging = false;
    document.body.classList.remove("is-resizing");
  };

  resizer.addEventListener("pointerup", stopDragging);
  resizer.addEventListener("pointercancel", stopDragging);
}

async function loadProjectTree() {
  activeProjectTree = await api("/api/projects/tree");
  if (!activeProjectId && activeProjectTree.projects && activeProjectTree.projects.length) {
    activeProjectId = activeProjectTree.projects[0].project.project_id;
    activeProjectSolverUrl = activeProjectTree.projects[0].project.solver_base_url || null;
    syncSolverSelector(activeProjectSolverUrl);
    log(`Default project selected: ${activeProjectId}`, "project");
  } else if (activeProjectId && activeProjectTree.projects) {
    const node = activeProjectTree.projects.find((item) => item.project.project_id === activeProjectId);
    if (node) {
      activeProjectSolverUrl = node.project.solver_base_url || null;
      syncSolverSelector(activeProjectSolverUrl);
    }
  }
  renderTree();
}

function ensureSolverOption(url) {
  if (!url) return;
  const select = $("solver-endpoint-select");
  if (!select) return;
  const exists = Array.from(select.options).some((option) => option.value === url);
  if (!exists) {
    const option = document.createElement("option");
    option.value = url;
    option.textContent = url;
    select.appendChild(option);
  }
}

function syncSolverSelector(url) {
  const select = $("solver-endpoint-select");
  const input = $("solver-endpoint-input");
  if (!select) return;
  const normalized = (url || "").trim();
  ensureSolverOption(normalized);
  select.value = normalized;
  if (input) {
    input.value = normalized;
  }
}

function selectedSolverEndpoint() {
  const select = $("solver-endpoint-select");
  const input = $("solver-endpoint-input");
  if (input && input.value.trim()) {
    return input.value.trim();
  }
  if (!select) return null;
  const value = select.value.trim();
  return value || null;
}

function renderTree() {
  const treeEl = $("project-tree");
  treeEl.innerHTML = "";

  if (!activeProjectTree || !activeProjectTree.projects.length) {
    treeEl.innerHTML = '<div class="placeholder">No projects yet. Create one to begin.</div>';
    return;
  }

  for (const node of activeProjectTree.projects) {
    const group = document.createElement("div");
    group.className = "tree-group";

    const projectRow = document.createElement("button");
    projectRow.type = "button";
    projectRow.className = "tree-project" + (node.project.project_id === activeProjectId ? " active" : "");
    const solverLabel = node.project.solver_base_url ? `solver: ${node.project.solver_base_url}` : "solver: internal mock";
    projectRow.innerHTML = `<strong>${escapeHtml(node.project.project_name)}</strong><span class="case-meta">${escapeHtml(solverLabel)}</span>`;
    projectRow.addEventListener("click", async () => {
      activeProjectId = node.project.project_id;
      activeProjectSolverUrl = node.project.solver_base_url || null;
      syncSolverSelector(activeProjectSolverUrl);
      activeCaseId = null;
      $("active-case-label").textContent = `${activeProjectId} / (no case selected)`;
      $("conditions-json").value = "";
      $("grid-json").value = "";
      latestPlanId = null;
      latestRunId = null;
      latestPlanStatus = null;
      activeThreadId = null;
      reportPage = 1;
      updateSolveStatus();
      renderTree();
      await refreshReports();
      log(`Selected project ${activeProjectId}`, "project");
    });
    group.appendChild(projectRow);

    for (const caseItem of node.cases) {
      const caseRow = document.createElement("button");
      caseRow.type = "button";
      caseRow.className = "tree-case" + (caseItem.project_id === activeProjectId && caseItem.case_id === activeCaseId ? " active" : "");
      caseRow.innerHTML = `<span><strong>${escapeHtml(caseItem.case_id)}</strong><div class="case-meta">rev ${caseItem.revision}</div></span><span class="case-meta">${escapeHtml(caseItem.source_yaml_path)}</span>`;
      caseRow.addEventListener("click", () => selectCase(caseItem.project_id, caseItem.case_id));
      group.appendChild(caseRow);
    }

    treeEl.appendChild(group);
  }
}

async function selectCase(projectId, caseId) {
  activeProjectId = projectId;
  activeCaseId = caseId;
  const caseData = await api(`/api/projects/${encodeURIComponent(projectId)}/cases/${encodeURIComponent(caseId)}`);
  $("active-case-label").textContent = `${projectId} / ${caseId} · rev ${caseData.revision}`;
  $("conditions-json").value = JSON.stringify(caseData.conditions, null, 2);
  $("grid-json").value = JSON.stringify(caseData.grid, null, 2);
  latestPlanId = null;
  latestRunId = null;
  latestPlanStatus = null;
  activeThreadId = null;
  reportPage = 1;
  log(`Selected ${projectId}/${caseId}`, "select");
  renderTree();
  await refreshReports();
}

async function createProject() {
  const projectName = $("project-name-input").value.trim();
  if (!projectName) return;
  const solverEndpoint = selectedSolverEndpoint();
  await api("/api/projects/", {
    method: "POST",
    body: JSON.stringify({ project_name: projectName, solver_base_url: solverEndpoint }),
  });
  activeProjectId = projectName;
  activeProjectSolverUrl = solverEndpoint;
  activeCaseId = null;
  $("project-name-input").value = "";
  log(`Created project ${projectName}`, "create");
  await loadProjectTree();
}

async function saveSolverEndpoint() {
  if (!activeProjectId) throw new Error("Select a project first.");
  const solverEndpoint = selectedSolverEndpoint();
  const updated = await api(`/api/projects/${encodeURIComponent(activeProjectId)}/solver-endpoint`, {
    method: "PUT",
    body: JSON.stringify({ solver_base_url: solverEndpoint }),
  });
  activeProjectSolverUrl = updated.solver_base_url || null;
  syncSolverSelector(activeProjectSolverUrl);
  log(`Saved solver endpoint for ${activeProjectId}: ${activeProjectSolverUrl || "internal mock"}`, "project");
  await loadProjectTree();
}

async function importCase() {
  if (!activeProjectId) {
    throw new Error("Select a project first in Projects / Cases.");
  }
  const explicitFile = $("source-yaml-file").files && $("source-yaml-file").files.length ? $("source-yaml-file").files[0] : null;
  if (!explicitFile) {
    throw new Error("Select a YAML file first.");
  }

  const caseName = inferCaseName(explicitFile);
  if (!caseName) {
    throw new Error("Could not infer case name from the selected YAML file.");
  }

  const tryImport = async (overwrite) => {
    const yamlFile = explicitFile;
    const formData = new FormData();
    formData.append("case_name", caseName);
    formData.append("source_yaml", yamlFile, yamlFile.name);
    formData.append("overwrite", String(overwrite));
    const response = await fetch(`/api/projects/${encodeURIComponent(activeProjectId)}/cases/import-upload`, {
      method: "POST",
      body: formData,
    });
    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;
    if (!response.ok) {
      const detail = payload && payload.detail ? payload.detail : text || response.statusText;
      throw new Error(detail);
    }
  };

  try {
    await tryImport(false);
  } catch (error) {
    if (!/already exists/i.test(error.message || "")) {
      throw error;
    }
    const confirmed = window.confirm(`Case '${caseName}' already exists. Overwrite by creating a new revision?`);
    if (!confirmed) {
      throw error;
    }
    await tryImport(true);
    log(`Overwrote existing case ${caseName} (new revision created).`, "import");
  }

  log(`Imported case ${caseName}`, "import");
  await loadProjectTree();
  await selectCase(activeProjectId, caseName);
}

function inferCaseName(yamlFile) {
  let candidate = "";
  if (yamlFile && yamlFile.name) {
    candidate = yamlFile.name;
  }
  candidate = candidate.replace(/\.ya?ml$/i, "").trim();
  candidate = candidate.replace(/[^A-Za-z0-9._-]/g, "_");
  return candidate;
}

async function saveCase() {
  if (!activeProjectId || !activeCaseId) throw new Error("Select a case first.");
  const payload = {
    conditions: JSON.parse($("conditions-json").value || "{}"),
    grid: JSON.parse($("grid-json").value || "{}"),
    approved: true,
    approval_comment: "Updated from GUI shell",
  };
  const result = await api(`/api/projects/${encodeURIComponent(activeProjectId)}/cases/${encodeURIComponent(activeCaseId)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  $("active-case-label").textContent = `${activeProjectId} / ${activeCaseId} · rev ${result.revision}`;
  log(`Saved case ${activeCaseId} revision ${result.revision}`, "update");
  await loadProjectTree();
}

async function createPlan() {
  if (!activeProjectId || !activeCaseId) throw new Error("Select a case first.");
  const instruction = $("chat-instruction").value.trim();
  if (!instruction) throw new Error("Instruction is required.");

  const parameterAxesRaw = $("parameter-axes").value.trim();
  const postprocessRaw = $("postprocess-policy").value.trim();

  let parameterAxes = null;
  let parameterAxesHint = null;
  if (parameterAxesRaw) {
    try {
      const parsed = JSON.parse(parameterAxesRaw);
      if (parsed && typeof parsed === "object") {
        parameterAxes = parsed;
      } else {
        parameterAxesHint = parameterAxesRaw;
      }
    } catch {
      parameterAxesHint = parameterAxesRaw;
    }
  }

  let postprocessPolicy = null;
  let postprocessAdditional = null;
  if (postprocessRaw) {
    try {
      const parsed = JSON.parse(postprocessRaw);
      if (parsed && typeof parsed === "object") {
        postprocessPolicy = parsed;
      } else {
        postprocessAdditional = postprocessRaw;
      }
    } catch {
      postprocessAdditional = postprocessRaw;
    }
  }

  const response = await api(`/api/projects/${encodeURIComponent(activeProjectId)}/cases/${encodeURIComponent(activeCaseId)}/chat/plans`, {
    method: "POST",
    body: JSON.stringify({
      instruction,
      parameter_axes: parameterAxes,
      parameter_axes_hint: parameterAxesHint,
      postprocess_policy: postprocessPolicy,
      postprocess_additional: postprocessAdditional,
      thread_id: activeThreadId,
    }),
  });
  activeThreadId = response.plan.thread_id;
  latestPlanId = response.plan.plan_id;
  latestPlanStatus = response.plan.approval_state;
  log(`Created plan ${latestPlanId} on ${activeThreadId}`, "plan");
  renderPlanPreview(response.plan);
  setTabs("solve");
  updateSolveStatus();
}

function renderPlanPreview(plan) {
  const preview = $("plan-preview");
  if (!preview) return;

  // Instruction
  $("preview-instruction").textContent = plan.instruction || "";

  // Parameter axes table
  const axes = plan.parameter_axes || {};
  const tbody = $("preview-axes-body");
  tbody.innerHTML = "";
  const axisEntries = Object.entries(axes);
  if (axisEntries.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="3" class="placeholder">No parameter sweep — single baseline run.</td>';
    tbody.appendChild(tr);
    $("preview-run-count").textContent = "Estimated runs: 1";
  } else {
    let totalRuns = 1;
    for (const [param, values] of axisEntries) {
      const tr = document.createElement("tr");
      const valueList = Array.isArray(values) ? values : [values];
      totalRuns *= valueList.length;
      tr.innerHTML = `<td class="param-name">${escapeHtml(param)}</td><td class="param-values">${valueList.map(v => escapeHtml(String(v))).join(", ")}</td><td class="param-count">${valueList.length}</td>`;
      tbody.appendChild(tr);
    }
    $("preview-run-count").textContent = `Estimated runs: ${totalRuns}`;
  }

  // Assumptions
  const ul = $("preview-assumptions");
  ul.innerHTML = "";
  (plan.assumptions || []).forEach(a => {
    const li = document.createElement("li");
    li.textContent = a;
    ul.appendChild(li);
  });

  // Badge
  const badge = $("plan-approval-badge");
  badge.textContent = plan.approval_state === "approved" ? "APPROVED" : "PENDING APPROVAL";
  badge.className = `badge badge-${plan.approval_state === "approved" ? "approved" : "pending"}`;

  preview.classList.remove("hidden");
}

async function approvePlan() {
  if (!latestPlanId) throw new Error("Create a plan first.");
  const response = await api(`/api/projects/${encodeURIComponent(activeProjectId)}/cases/${encodeURIComponent(activeCaseId)}/chat/plans/${encodeURIComponent(latestPlanId)}/approve`, {
    method: "POST",
  });
  latestPlanStatus = response.plan.approval_state;
  log(`Approved plan ${latestPlanId}`, "approve");
  const badge = $("plan-approval-badge");
  if (badge) {
    badge.textContent = "APPROVED";
    badge.className = "badge badge-approved";
  }
  updateSolveStatus();
}

async function runPlan() {
  if (!latestPlanId) throw new Error("Create a plan first.");
  const response = await api(`/api/projects/${encodeURIComponent(activeProjectId)}/cases/${encodeURIComponent(activeCaseId)}/runs`, {
    method: "POST",
    body: JSON.stringify({ plan_id: latestPlanId }),
  });
  latestRunId = response.run_id;
  log(`Run queued ${latestRunId}`, response.status);
  updateSolveStatus();
  pollRunStatus();
}

async function pollRunStatus() {
  if (!latestRunId) return;
  const timer = window.setInterval(async () => {
    try {
      const run = await api(`/api/projects/${encodeURIComponent(activeProjectId)}/cases/${encodeURIComponent(activeCaseId)}/runs/${encodeURIComponent(latestRunId)}`);
      $("run-status").textContent = `Run ${run.run_id}: ${run.status}`;
      if (run.status === "completed" || run.status === "failed") {
        window.clearInterval(timer);
        await refreshReports();
      }
    } catch (error) {
      window.clearInterval(timer);
      log(error.message, "run-error");
    }
  }, 300);
}

function updateSolveStatus() {
  $("run-status").textContent = `Plan: ${latestPlanId || "none"} · state: ${latestPlanStatus || "none"}`;
}

function reportSelectionId(report) {
  return String(report?.report_bundle_id || report?.run_id || "").trim();
}

function formatLegendName(name, fallback) {
  const raw = String(name || fallback || "").trim();
  if (!raw) return "series";
  return raw
    .replace(/^external[_-]?result[:_]?/i, "")
    .replace(/^\s+|\s+$/g, "")
    .replace(/^:+/, "")
    .trim();
}

function buildPlotTraces(reportSeriesList, plot, includeReportPrefix) {
  return reportSeriesList.flatMap(({ report, plotPayload }) => {
    const tracePayload = Array.isArray(plotPayload.traces) && plotPayload.traces.length
      ? plotPayload.traces
      : [{ name: report.run_id, series: plotPayload.series || {} }];

    return tracePayload.flatMap((traceItem) => {
      const series = traceItem.series || {};
      const xRaw = Array.isArray(series.x) ? series.x : [];
      const yRaw = Array.isArray(series[plot.key]) ? series[plot.key] : [];
      const count = Math.min(xRaw.length, yRaw.length);
      if (count === 0) return [];

      const x = xRaw.slice(0, count);
      let y = yRaw.slice(0, count);
      if (plot.scale) {
        y = y.map((value) => value * plot.scale);
      }

      const baseName = formatLegendName(traceItem.name, report.run_id);
      const name = includeReportPrefix ? `${report.run_id}:${baseName}` : baseName;
      return [{
        x,
        y,
        name,
        type: "scatter",
        mode: "lines",
        line: { width: 2 },
      }];
    });
  });
}

function renderGraphGrid(containerEl, reportSeriesList, options = {}) {
  if (!reportSeriesList.length) {
    containerEl.innerHTML = '<div class="placeholder">No plot series available. Confirm run artifacts include results.csv.</div>';
    return;
  }

  const idPrefix = options.idPrefix || "plot";
  const includeReportPrefix = options.includeReportPrefix === true;
  const note = options.note || `Plot source: ${reportSeriesList[0].plotPayload.source_csv_path || "unknown"}`;
  const plotIds = plotConfig.map((_, index) => `${idPrefix}-${index}`);

  containerEl.innerHTML = `
    <div class="results-note">${escapeHtml(note)}</div>
    <div class="graphs-grid">
      ${plotIds.map((plotId) => `<div id="${plotId}"></div>`).join("")}
    </div>
  `;

  plotConfig.forEach((plot, index) => {
    const plotEl = $(plotIds[index]);
    if (!plotEl) return;
    const traces = buildPlotTraces(reportSeriesList, plot, includeReportPrefix);
    if (!traces.length) {
      plotEl.innerHTML = `<div style="padding: 16px; color: #666;">No data for ${escapeHtml(plot.title)}</div>`;
      return;
    }

    const layout = {
      title: plot.title,
      xaxis: { title: "x (m)" },
      yaxis: { title: plot.yLabel },
      hovermode: "closest",
      plot_bgcolor: "#fafafa",
      paper_bgcolor: "white",
      legend: {
        x: 1,
        y: 1,
        xanchor: "right",
        yanchor: "top",
        bgcolor: "rgba(255,255,255,0.82)",
        bordercolor: "rgba(0,0,0,0.1)",
        borderwidth: 1,
        font: { size: 10 },
      },
      margin: { t: 40, r: 20, b: 40, l: 60 },
      font: { size: 11 },
    };

    Plotly.newPlot(plotEl, traces, layout, { responsive: true, displayModeBar: false });
  });
}

function renderCompareGroups(containerEl, reportSeriesList) {
  if (!reportSeriesList.length) {
    containerEl.innerHTML = '<div class="placeholder">Select reports to compare.</div>';
    return;
  }

  containerEl.innerHTML = `
    <div class="graphs-groups">
      ${reportSeriesList.map((item, index) => `
        <section class="graphs-group">
          <div id="graphs-group-${index}"></div>
        </section>
      `).join("")}
    </div>
  `;

  reportSeriesList.forEach((entry, index) => {
    const groupEl = $(`graphs-group-${index}`);
    if (!groupEl) return;
    renderGraphGrid(groupEl, [entry], {
      idPrefix: `group-${index}`,
      includeReportPrefix: false,
      note: `Report ${entry.report.report_bundle_id} · run ${entry.report.run_id} · source ${entry.plotPayload.source_csv_path || "unknown"}`,
    });
  });
}

function renderReportList(listEl, reports) {
  listEl.innerHTML = reports.length
    ? reports.map((report) => {
      const selectionId = reportSelectionId(report);
      const checked = selectedCompareReportIds.has(selectionId) ? "checked" : "";
      return `
        <div class="report-item">
          <div class="report-item-head">
            <strong>${escapeHtml(report.report_bundle_id)}</strong>
            <label class="report-compare-pick">
              <input class="report-compare-checkbox" type="checkbox" data-report-id="${escapeHtml(selectionId)}" ${checked} />
              compare
            </label>
          </div>
          <div>${escapeHtml(report.summary)}</div>
          <small>${escapeHtml(report.created_at)} · run ${escapeHtml(report.run_id)}</small>
        </div>
      `;
    }).join("")
    : '<div class="placeholder">No reports yet.</div>';
}

function updateGraphCompareControls() {
  const compareMode = $("graphs-compare-mode");
  const compareView = $("graphs-compare-view");
  const selectVisible = $("graphs-select-visible-btn");
  const clearSelection = $("graphs-clear-selection-btn");
  const note = $("graphs-mode-note");

  if (compareMode) compareMode.checked = compareModeEnabled;
  if (compareView) {
    compareView.value = compareViewMode;
    compareView.disabled = !compareModeEnabled;
  }
  if (selectVisible) selectVisible.disabled = !compareModeEnabled || !currentReportPage.length;
  if (clearSelection) clearSelection.disabled = !compareModeEnabled || selectedCompareReportIds.size === 0;
  if (note) {
    note.textContent = compareModeEnabled
      ? `Compare mode: ${selectedCompareReportIds.size} selected (${compareViewMode === "overlay" ? "overlay" : "separate groups"}).`
      : "Default mode: latest report in selected case.";
  }
}

async function refreshGraphs() {
  const graphsEl = $("graphs-view");
  if (!graphsEl) return;
  if (!activeCaseId) {
    graphsEl.innerHTML = '<div class="placeholder">Select a case in Conditions to view graphs.</div>';
    updateGraphCompareControls();
    return;
  }
  if (!currentReportPage.length) {
    graphsEl.innerHTML = '<div class="placeholder">No reports yet. Run an approved plan to see results.</div>';
    updateGraphCompareControls();
    return;
  }

  if (!compareModeEnabled) {
    const latestReport = currentReportPage[0];
    const reportSeriesList = await loadPlotSeriesForReports(activeProjectId, activeCaseId || latestReport.case_id, [latestReport]);
    renderGraphGrid(graphsEl, reportSeriesList, { idPrefix: "plot", includeReportPrefix: false });
    updateGraphCompareControls();
    return;
  }

  const selectedReports = currentReportPage.filter((report) => selectedCompareReportIds.has(reportSelectionId(report)));
  if (!selectedReports.length) {
    graphsEl.innerHTML = '<div class="placeholder">Compare mode is ON. Select report entries in the Report tab list.</div>';
    updateGraphCompareControls();
    return;
  }

  const reportSeriesList = await loadPlotSeriesForReports(activeProjectId, activeCaseId || selectedReports[0].case_id, selectedReports);
  if (compareViewMode === "separate") {
    renderCompareGroups(graphsEl, reportSeriesList);
  } else {
    renderGraphGrid(graphsEl, reportSeriesList, {
      idPrefix: "compare",
      includeReportPrefix: true,
      note: `Compare overlay: ${reportSeriesList.length} selected reports`,
    });
  }
  updateGraphCompareControls();
}

async function loadPlotSeriesForReports(projectId, caseId, reports) {
  const tasks = reports.map(async (report) => {
    try {
      const reportCaseId = report.case_id || caseId;
      const plotPayload = await api(
        `/api/projects/${encodeURIComponent(projectId)}/cases/${encodeURIComponent(reportCaseId)}/runs/${encodeURIComponent(report.run_id)}/plot-series`
      );
      return { report, plotPayload };
    } catch (error) {
      log(`Plot data unavailable for ${report.run_id}: ${error.message}`, "plot");
      return null;
    }
  });
  const results = await Promise.all(tasks);
  return results.filter(Boolean);
}

async function refreshReports() {
  if (!activeProjectId) return;
  const query = new URLSearchParams();
  if (activeCaseId) query.set("case_id", activeCaseId);
  if (latestPlanId) query.set("plan_id", latestPlanId);
  query.set("sort_by", $("report-sort-by") ? $("report-sort-by").value : "created_at");
  query.set("sort_order", $("report-sort-order") ? $("report-sort-order").value : "desc");
  query.set("page", String(reportPage));
  query.set("page_size", String(reportPageSize));
  const response = await api(`/api/projects/${encodeURIComponent(activeProjectId)}/reports${query.toString() ? "?" + query.toString() : ""}`);
  const listEl = $("report-list");
  const pageLabel = $("report-page-label");
  const prevButton = $("report-prev-page");
  const nextButton = $("report-next-page");
  currentReportPage = Array.isArray(response.reports) ? response.reports : [];

  const visibleIds = new Set(currentReportPage.map((report) => reportSelectionId(report)));
  for (const selectedId of Array.from(selectedCompareReportIds)) {
    if (!visibleIds.has(selectedId)) {
      selectedCompareReportIds.delete(selectedId);
    }
  }

  if (pageLabel) {
    const totalPages = Math.max(1, Math.ceil((response.total_count || 0) / response.page_size));
    pageLabel.textContent = `Page ${response.page} / ${totalPages} (${response.total_count} total)`;
  }
  if (prevButton) prevButton.disabled = response.page <= 1;
  if (nextButton) nextButton.disabled = response.page * response.page_size >= response.total_count;
  renderReportList(listEl, currentReportPage);

  // Populate Graphs tab with case-scoped default and compare modes.
  const tableEl = $("table-view");
  await refreshGraphs();

  if (currentReportPage.length > 0) {
    const latestReport = currentReportPage[0];
    
    // Populate Table tab with run summary
    tableEl.innerHTML = `
      <div class="results-panel">
        <div class="results-title">Run Summary</div>
        <table class="results-table">
          <tr><th>Report ID</th><td>${escapeHtml(latestReport.report_bundle_id)}</td></tr>
          <tr><th>Plan ID</th><td>${escapeHtml(latestReport.plan_id)}</td></tr>
          <tr><th>Run ID</th><td>${escapeHtml(latestReport.run_id)}</td></tr>
          <tr><th>Case ID</th><td>${escapeHtml(latestReport.case_id)}</td></tr>
          <tr><th>Created</th><td>${escapeHtml(latestReport.created_at)}</td></tr>
          <tr><th>Summary</th><td>${escapeHtml(latestReport.summary)}</td></tr>
        </table>
      </div>
    `;
  } else {
    tableEl.innerHTML = '<div class="placeholder">No reports yet. Run an approved plan to see results.</div>';
  }
}

document.querySelectorAll(".tab-btn").forEach((button) => {
  button.addEventListener("click", () => setTabs(button.dataset.tab));
});

$("report-sort-by")?.addEventListener("change", async () => {
  reportPage = 1;
  await refreshReports();
});

$("report-sort-order")?.addEventListener("change", async () => {
  reportPage = 1;
  await refreshReports();
});

$("graphs-compare-mode")?.addEventListener("change", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) return;
  compareModeEnabled = target.checked;
  if (compareModeEnabled && selectedCompareReportIds.size === 0) {
    currentReportPage.forEach((report) => {
      selectedCompareReportIds.add(reportSelectionId(report));
    });
    renderReportList($("report-list"), currentReportPage);
  }
  await refreshGraphs();
});

$("graphs-compare-view")?.addEventListener("change", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) return;
  compareViewMode = target.value === "separate" ? "separate" : "overlay";
  await refreshGraphs();
});

$("solver-endpoint-select")?.addEventListener("change", () => {
  const input = $("solver-endpoint-input");
  const select = $("solver-endpoint-select");
  if (!input || !select) return;
  input.value = select.value;
});

document.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  if (target.id === "create-project-btn") {
    try { await createProject(); } catch (error) { log(error.message, "error"); }
  }
  if (target.id === "save-solver-endpoint-btn") {
    try { await saveSolverEndpoint(); } catch (error) { log(error.message, "error"); }
  }
  if (target.id === "import-case-btn") {
    try { await importCase(); } catch (error) { log(error.message, "error"); }
  }
  if (target.id === "save-conditions-btn" || target.id === "save-grid-btn") {
    try { await saveCase(); } catch (error) { log(error.message, "error"); }
  }
  if (target.id === "create-plan-btn") {
    try { await createPlan(); } catch (error) { log(error.message, "error"); }
  }
  if (target.id === "approve-plan-btn") {
    try { await approvePlan(); } catch (error) { log(error.message, "error"); }
  }
  if (target.id === "run-plan-btn") {
    try { await runPlan(); } catch (error) { log(error.message, "error"); }
  }
  if (target.id === "report-prev-page") {
    reportPage = Math.max(1, reportPage - 1);
    try { await refreshReports(); } catch (error) { log(error.message, "error"); }
  }
  if (target.id === "report-next-page") {
    reportPage += 1;
    try { await refreshReports(); } catch (error) { log(error.message, "error"); }
  }
  if (target.id === "graphs-select-visible-btn") {
    currentReportPage.forEach((report) => {
      selectedCompareReportIds.add(reportSelectionId(report));
    });
    renderReportList($("report-list"), currentReportPage);
    try { await refreshGraphs(); } catch (error) { log(error.message, "error"); }
  }
  if (target.id === "graphs-clear-selection-btn") {
    selectedCompareReportIds.clear();
    renderReportList($("report-list"), currentReportPage);
    try { await refreshGraphs(); } catch (error) { log(error.message, "error"); }
  }
});

document.addEventListener("change", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) return;
  if (!target.classList.contains("report-compare-checkbox")) return;
  const reportId = String(target.dataset.reportId || "").trim();
  if (!reportId) return;
  if (target.checked) {
    selectedCompareReportIds.add(reportId);
  } else {
    selectedCompareReportIds.delete(reportId);
  }
  if (compareModeEnabled) {
    try { await refreshGraphs(); } catch (error) { log(error.message, "error"); }
  } else {
    updateGraphCompareControls();
  }
});

(async function bootstrap() {
  try {
    initPaneResizer();
    updateGraphCompareControls();
    await loadProjectTree();
    log("GUI shell ready.", "ready");
  } catch (error) {
    log(error.message, "error");
  }
})();
