function qs(s) {
  return document.querySelector(s);
}

/** Safari: el input file a veces no conserva files tras DataTransfer. */
let importsSelectedFile = null;

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** No redefinir apiJson/getToken/setToken: portal.js ya los expone (imports.js se carga después). */
const API_BASE = typeof PORTAL_API_BASE !== "undefined" ? PORTAL_API_BASE : apiBase();

async function importsApiJson(path, opts = {}) {
  const headers = Object.assign({}, opts.headers || {});
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const url = `${API_BASE}${path}`;
  let res;
  try {
    res = await fetch(url, Object.assign({}, opts, { headers }));
  } catch (e) {
    throw new Error(`Red: ${e && e.message ? e.message : e}`);
  }
  const text = await res.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    const msg =
      typeof body === "string"
        ? body
        : body && body.detail
          ? typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail)
          : JSON.stringify(body);
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }
  return body;
}

function setStatus(msg, kind = "neutral") {
  const el = qs("#status");
  if (!el) return;
  el.textContent = msg || "";
  el.classList.remove("ok", "error", "imports-status");
  el.classList.add("imports-status");
  if (kind === "ok") el.classList.add("ok");
  if (kind === "error") el.classList.add("error");
}

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES");
  } catch {
    return String(iso);
  }
}

function renderPreviewTable(body, containerId) {
  const el = qs(containerId);
  if (!el) return;
  const cols = body.columns || [];
  const rows = body.sample_rows || [];
  const q = body.quality_summary;
  let alerts = "";
  if (q?.alerts?.length) {
    alerts = `<ul class="imports-alert-list">${q.alerts.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}</ul>`;
  }
  const head = cols.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
  const bodyRows = rows
    .map((r) => {
      const cells = cols.map((c) => `<td>${escapeHtml(String(r.fields?.[c] ?? ""))}</td>`).join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  el.innerHTML = `
    <div class="imports-visual__meta">
      <span class="imports-pill">${body.total_rows} filas</span>
      <span class="imports-pill">Completitud ${Math.round((q?.completeness_ratio || 0) * 100)}%</span>
    </div>
    ${alerts}
    <div class="patients-table-wrap"><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${bodyRows}</tbody></table></div>`;
  el.hidden = false;
}

function showPipelineResults(visible) {
  const card = qs("#pipelineResults");
  if (!card) return;
  card.hidden = !visible;
  card.setAttribute("aria-hidden", visible ? "false" : "true");
}

function renderSyncKpis(sync) {
  const el = qs("#syncKpis");
  if (!el || !sync) return;
  showPipelineResults(true);
  const items = [
    ["Pacientes nuevos", sync.patients_created],
    ["Pacientes actualizados", sync.patients_updated],
    ["Médicos nuevos", sync.medicos_created],
    ["Usuarios nuevos", sync.users_created],
    ["Usuarios vinculados", sync.users_linked],
  ];
  el.innerHTML = items
    .map(
      ([label, val]) => `<div class="imports-kpi"><span class="imports-kpi__val">${val ?? 0}</span><span class="imports-kpi__lbl">${label}</span></div>`,
    )
    .join("");
}

function renderMlKpis(metrics) {
  const el = qs("#mlKpis");
  const hint = qs("#mlHint");
  if (!metrics || !el) return;
  const mean = metrics.cv_accuracy_mean != null ? `${(metrics.cv_accuracy_mean * 100).toFixed(1)}%` : "—";
  const std = metrics.cv_accuracy_std != null ? `${(metrics.cv_accuracy_std * 100).toFixed(1)}%` : "";
  el.innerHTML = `
    <div class="imports-kpi"><span class="imports-kpi__val">${mean}</span><span class="imports-kpi__lbl">Accuracy CV (${metrics.cv_folds || 5} folds)</span></div>
    <div class="imports-kpi"><span class="imports-kpi__val">${metrics.n_samples ?? "—"}</span><span class="imports-kpi__lbl">Muestras</span></div>
    <div class="imports-kpi"><span class="imports-kpi__val">${metrics.n_classes ?? "—"}</span><span class="imports-kpi__lbl">Clases de enfermedad</span></div>`;
  if (hint && metrics.classes?.length) {
    hint.textContent = `Clases: ${metrics.classes.join(", ")}`;
  }
}

let mlCharts = { cv: null, dist: null, f1: null, feat: null };

function destroyMlCharts() {
  Object.keys(mlCharts).forEach((k) => {
    if (mlCharts[k]) {
      mlCharts[k].destroy();
      mlCharts[k] = null;
    }
  });
}

function waitForChartJs(maxMs = 8000) {
  return new Promise((resolve) => {
    if (typeof Chart !== "undefined") {
      resolve(true);
      return;
    }
    const t0 = Date.now();
    const tick = () => {
      if (typeof Chart !== "undefined") resolve(true);
      else if (Date.now() - t0 > maxMs) resolve(false);
      else setTimeout(tick, 80);
    };
    tick();
  });
}

function pctMl(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${(100 * n).toFixed(1)}%`;
}

function setMlStudioStatus(msg, kind = "neutral") {
  const el = qs("#mlStudioStatus");
  if (!el) return;
  el.textContent = msg || "";
  el.classList.remove("ok", "error", "ml-studio__status--ok", "ml-studio__status--error");
  if (kind === "ok") el.classList.add("ok", "ml-studio__status--ok");
  if (kind === "error") el.classList.add("error", "ml-studio__status--error");
}

function updateAccuracyRing(pct) {
  const fg = document.getElementById("mlAccuracyRingFg");
  const val = qs("#mlAccuracyRingVal");
  if (val) val.textContent = pct != null && !Number.isNaN(pct) ? `${(pct * 100).toFixed(1)}%` : "—";
  if (fg) {
    const c = 2 * Math.PI * 52;
    fg.style.strokeDasharray = `${c}`;
    fg.style.strokeDashoffset = pct != null && !Number.isNaN(pct) ? `${c * (1 - Math.max(0, Math.min(1, pct)))}` : `${c}`;
  }
}

function renderBarFallback(containerId, labels, values, suffix = "%") {
  const el = qs(containerId);
  if (!el || !labels.length) return;
  const max = Math.max(...values, 0.01);
  el.hidden = false;
  el.innerHTML = labels
    .map((label, i) => {
      const v = values[i];
      const w = Math.max(4, Math.round((100 * v) / max));
      return `<div class="ml-fbar"><span class="ml-fbar__lbl">${escapeHtml(label)}</span><span class="ml-fbar__track"><span style="width:${w}%"></span></span><span class="ml-fbar__val">${v.toFixed(1)}${suffix}</span></div>`;
    })
    .join("");
}

function hideFallbacks() {
  ["#chartCvFallback", "#chartDistFallback", "#chartF1Fallback", "#chartFeatFallback"].forEach((sel) => {
    const el = qs(sel);
    if (el) el.hidden = true;
  });
}

function renderMlStudioKpis(m) {
  const el = qs("#mlStudioKpis");
  if (!el) return;
  const mean = m.cv_accuracy_mean != null ? pctMl(m.cv_accuracy_mean) : "—";
  const std = m.cv_accuracy_std != null ? pctMl(m.cv_accuracy_std) : "—";
  const trained = m.trained_at ? fmtDate(m.trained_at) : "Sin entrenar";
  el.innerHTML = `
    <div class="ml-studio-kpi ml-studio-kpi--hero">
      <span class="ml-studio-kpi__val">${mean}</span>
      <span class="ml-studio-kpi__lbl">Accuracy media (CV)</span>
    </div>
    <div class="ml-studio-kpi"><span class="ml-studio-kpi__val">± ${std}</span><span class="ml-studio-kpi__lbl">Desv. folds</span></div>
    <div class="ml-studio-kpi"><span class="ml-studio-kpi__val">${m.n_samples ?? 0}</span><span class="ml-studio-kpi__lbl">Muestras</span></div>
    <div class="ml-studio-kpi"><span class="ml-studio-kpi__val">${m.n_classes ?? 0}</span><span class="ml-studio-kpi__lbl">Clases</span></div>
    <div class="ml-studio-kpi"><span class="ml-studio-kpi__val">${m.cv_folds ?? "—"}</span><span class="ml-studio-kpi__lbl">Folds</span></div>
    <div class="ml-studio-kpi"><span class="ml-studio-kpi__val">${escapeHtml(trained)}</span><span class="ml-studio-kpi__lbl">Entrenado</span></div>`;
}

function renderConfusionMatrix(cm, classes) {
  const section = qs("#mlConfusionSection");
  const wrap = qs("#mlConfusionWrap");
  if (!section || !wrap || !cm?.length || !classes?.length) {
    if (section) section.hidden = true;
    return;
  }
  const max = Math.max(...cm.flat(), 1);
  const head = classes.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
  const rows = cm
    .map((row, i) => {
      const cells = row
        .map((v, j) => {
          const intensity = Math.round((100 * v) / max);
          const diag = i === j ? " ml-cm__diag" : "";
          return `<td class="ml-cm__cell${diag}" style="--intensity:${intensity}%">${v}</td>`;
        })
        .join("");
      return `<tr><th scope="row">${escapeHtml(classes[i])}</th>${cells}</tr>`;
    })
    .join("");
  wrap.innerHTML = `<table class="ml-cm-table"><thead><tr><th></th>${head}</tr></thead><tbody>${rows}</tbody></table>`;
  section.hidden = false;
}

async function renderMlStudioCharts(m) {
  hideFallbacks();
  const cvCanvas = qs("#chartCvScores");
  const dist = m.class_distribution || {};
  const distLabels = Object.keys(dist);
  const pcm = m.per_class_metrics || {};
  const f1Labels = Object.keys(pcm);
  const fi = m.feature_importance || {};
  const fiLabels = Object.keys(fi);

  const scores = (m.cv_scores || []).map((s) => s * 100);
  if (scores.length) {
    renderBarFallback("#chartCvFallback", scores.map((_, i) => `Fold ${i + 1}`), scores, "%");
  }
  if (distLabels.length) {
    renderBarFallback(
      "#chartDistFallback",
      distLabels,
      distLabels.map((k) => dist[k]),
      "",
    );
  }

  if (f1Labels.length) {
    renderBarFallback(
      "#chartF1Fallback",
      f1Labels,
      f1Labels.map((k) => (pcm[k]["f1-score"] ?? 0) * 100),
      "%",
    );
  }

  if (fiLabels.length) {
    renderBarFallback("#chartFeatFallback", fiLabels, fiLabels.map((k) => fi[k] * 100), "%");
  }

  const ready = await waitForChartJs();
  if (!ready) {
    [cvCanvas, qs("#chartClassDist"), qs("#chartClassF1"), qs("#chartFeatImp")].forEach((c) => {
      if (c?.parentElement) c.hidden = true;
    });
    renderConfusionMatrix(m.confusion_matrix, m.classes);
    return;
  }
  destroyMlCharts();
  [cvCanvas, qs("#chartClassDist"), qs("#chartClassF1"), qs("#chartFeatImp")].forEach((c) => {
    if (c) c.hidden = false;
  });
  hideFallbacks();

  if (cvCanvas && m.cv_scores?.length) {
    mlCharts.cv = new Chart(cvCanvas, {
      type: "bar",
      data: {
        labels: m.cv_scores.map((_, i) => `Fold ${i + 1}`),
        datasets: [{ label: "Accuracy", data: m.cv_scores.map((s) => s * 100), backgroundColor: "#14b8a6", borderRadius: 6 }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            min: 0,
            max: 100,
            ticks: { callback: (v) => `${v}%` },
          },
        },
      },
    });
  }

  const distCanvas = qs("#chartClassDist");
  if (distCanvas && distLabels.length) {
    mlCharts.dist = new Chart(distCanvas, {
      type: "doughnut",
      data: {
        labels: distLabels,
        datasets: [{
          data: distLabels.map((k) => dist[k]),
          backgroundColor: ["#0f766e", "#14b8a6", "#5eead4", "#f59e0b", "#ef4444", "#8b5cf6"],
        }],
      },
      options: { responsive: true, plugins: { legend: { position: "bottom" } } },
    });
  }

  const f1Canvas = qs("#chartClassF1");
  if (f1Canvas && f1Labels.length) {
    mlCharts.f1 = new Chart(f1Canvas, {
      type: "bar",
      data: {
        labels: f1Labels,
        datasets: [{
          label: "F1",
          data: f1Labels.map((k) => (pcm[k]["f1-score"] ?? 0) * 100),
          backgroundColor: "#0d9488",
          borderRadius: 4,
        }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            min: 0,
            max: 100,
            ticks: { callback: (v) => `${v}%` },
          },
        },
      },
    });
  }

  const featCanvas = qs("#chartFeatImp");
  if (featCanvas && fiLabels.length) {
    mlCharts.feat = new Chart(featCanvas, {
      type: "pie",
      data: {
        labels: fiLabels,
        datasets: [{ data: fiLabels.map((k) => fi[k] * 100), backgroundColor: ["#0f766e", "#99f6e4"] }],
      },
      options: { responsive: true, plugins: { legend: { position: "bottom" } } },
    });
  }

  renderConfusionMatrix(m.confusion_matrix, m.classes);
}

function renderMlStudio(metrics) {
  if (!metrics) return;
  updateAccuracyRing(metrics.cv_accuracy_mean);
  renderMlStudioKpis(metrics);
  void renderMlStudioCharts(metrics);
  const sub = qs("#mlStudioSub");
  if (sub) {
    sub.textContent =
      metrics.n_samples > 0
        ? `${metrics.n_samples} pacientes · ${metrics.n_classes} clases · edad, sexo, departamento`
        : metrics.message || "Importa referencia_enfermedades.csv y reentrena";
  }
  if (metrics.model_available && metrics.cv_accuracy_mean != null) {
    setMlStudioStatus(`Modelo activo · accuracy CV ${pctMl(metrics.cv_accuracy_mean)}`, "ok");
  } else {
    setMlStudioStatus(metrics.message || "Sin modelo entrenado. Pulsa «Reentrenar modelo».", "error");
  }
}

async function loadMlPredictions() {
  const tbody = qs("#mlPredictionsTbody");
  const empty = qs("#mlPredictionsEmpty");
  const badge = qs("#mlPredictionsCount");
  if (!tbody) return;
  try {
    const rows = await importsApiJson("/ml/patient-disease/predictions?limit=15");
    tbody.innerHTML = "";
    if (!rows?.length) {
      if (empty) empty.hidden = false;
      if (badge) badge.textContent = "0";
      return;
    }
    if (empty) empty.hidden = true;
    if (badge) badge.textContent = String(rows.length);
    for (const r of rows) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><code>${escapeHtml(r.patient_id)}</code></td>
        <td><span class="ml-pred-tag">${escapeHtml(r.predicted_diagnosis)}</span></td>
        <td>${r.confidence != null ? pctMl(r.confidence) : "—"}</td>`;
      tbody.appendChild(tr);
    }
  } catch {
    if (empty) empty.hidden = false;
    if (badge) badge.textContent = "—";
  }
}

async function loadMlStudio() {
  setMlStudioStatus("Cargando métricas…");
  try {
    const m = await importsApiJson("/ml/patient-disease/metrics");
    renderMlStudio(m);
    await loadMlPredictions();
  } catch (e) {
    setMlStudioStatus(String(e.message || e), "error");
  }
}

async function retrainMlModel() {
  const btn = qs("#btnRetrainMl");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Entrenando…";
  }
  setMlStudioStatus("Validación cruzada en curso…");
  try {
    const m = await importsApiJson("/ml/patient-disease/train", { method: "POST" });
    renderMlStudio(m);
    renderMlKpis(m);
    showPipelineResults(true);
    await loadMlPredictions();
    setMlStudioStatus(m.message || "Modelo reentrenado.", "ok");
    setStatus(`ML: accuracy CV ${pctMl(m.cv_accuracy_mean)}`, "ok");
  } catch (e) {
    setMlStudioStatus(String(e.message || e), "error");
    setStatus(String(e.message || e), "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Reentrenar modelo";
    }
  }
}

async function doPreview() {
  const file = getImportFile();
  if (!file) {
    setStatus("Seleccione un fichero CSV.", "error");
    return;
  }
  setStatus("Generando vista previa…");
  const fd = new FormData();
  fd.append("file", file, file.name);
  const body = await importsApiJson("/imports/csv/preview?preview_limit=15", { method: "POST", body: fd });
  renderPreviewTable(body, "#previewVisual");
  setStatus("Vista previa lista.", "ok");
}

function getImportFile() {
  if (importsSelectedFile) return importsSelectedFile;
  const input = qs("#filePreview");
  return input?.files?.[0] || null;
}

function setImportFile(file) {
  importsSelectedFile = file || null;
  const input = qs("#filePreview");
  const hint = qs("#importsFileHint");
  if (file && hint) hint.textContent = `Fichero listo: ${file.name}`;
  if (file && input) {
    try {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
    } catch {
      /* Safari puede dejar input.files vacío; importsSelectedFile sigue válido */
    }
  }
}

const PIPELINE_ORDER = ["clean", "ingest", "transform", "analyze", "ml"];

const PIPELINE_STEP_LABELS = {
  clean: "Limpieza y calidad",
  ingest: "Ingesta en PostgreSQL",
  transform: "Transformación",
  analyze: "Análisis agregado",
  ml: "Modelo ML (árbol + CV)",
};

const PIPELINE_GUIDE = {
  clean: "Paso 1 de 5 · Revisamos columnas, vacíos y filas duplicadas.",
  ingest: "Paso 2 de 5 · Guardamos en patients, medicos y app_users.",
  transform: "Paso 3 de 5 · Agregados analíticos por lote.",
  analyze: "Paso 4 de 5 · Métricas del centro de control.",
  ml: "Paso 5 de 5 · Árbol de decisiones con validación cruzada.",
  done: "Pipeline finalizado. Datos en BD y modelo actualizado.",
  idle: "Selecciona un CSV (recomendado: Enfermedades ML) y pulsa iniciar.",
};

let pipelineStepsState = [];

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function setPipelineGuide(key) {
  const el = qs("#pipelineGuide");
  if (el) el.textContent = PIPELINE_GUIDE[key] || PIPELINE_GUIDE.idle;
}

function setPipelineProgress(fraction) {
  const fill = qs("#pipelineRailFill");
  if (fill) fill.style.width = `${Math.min(100, Math.max(0, fraction * 100))}%`;
}

function initPipelineSteps() {
  pipelineStepsState = PIPELINE_ORDER.map((stage) => ({
    stage,
    label: PIPELINE_STEP_LABELS[stage],
    status: "pending",
    message: "En espera…",
  }));
  renderPipelineSteps(pipelineStepsState, -1);
  setPipelineProgress(0);
}

function patchPipelineStep(index, patch) {
  pipelineStepsState[index] = { ...pipelineStepsState[index], ...patch };
  renderPipelineSteps(pipelineStepsState, patch.status === "running" ? index : -1);
}

function renderPipelineSteps(steps, activeIndex = -1) {
  const ol = qs("#pipelineSteps");
  if (!ol) return;
  ol.innerHTML = (steps || [])
    .map((s, i) => {
      const st = s.status || "pending";
      const cls =
        st === "running"
          ? "pipeline-step--active pipeline-step--running"
          : st === "ok"
            ? "pipeline-step--ok"
            : st === "warning"
              ? "pipeline-step--warn"
              : st === "error"
                ? "pipeline-step--error"
                : i === activeIndex
                  ? "pipeline-step--active"
                  : "pipeline-step--pending";
      const label = s.label || PIPELINE_STEP_LABELS[s.stage] || s.stage;
      const icon =
        st === "running"
          ? '<span class="pipeline-step__spinner" aria-hidden="true"></span>'
          : st === "ok"
            ? "✓"
            : st === "error"
              ? "!"
              : String(i + 1);
      return `<li class="pipeline-step ${cls}" id="pipeline-step-${s.stage}">
        <span class="pipeline-step__badge" aria-hidden="true">${icon}</span>
        <span class="pipeline-step__body">
          <p class="pipeline-step__title">${escapeHtml(label)}</p>
          <p class="pipeline-step__msg">${escapeHtml(s.message || "")}${s.duration_ms != null ? ` · ${s.duration_ms} ms` : ""}</p>
        </span>
      </li>`;
    })
    .join("");
  const active = steps[activeIndex];
  if (active && active.status === "running") {
    const node = qs(`#pipeline-step-${active.stage}`);
    node?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function formWithFile(file) {
  const fd = new FormData();
  fd.append("file", file, file.name);
  return fd;
}

async function runPipelineStep(index, file, run) {
  const t0 = performance.now();
  patchPipelineStep(index, { status: "running", message: "En curso…" });
  setPipelineGuide(PIPELINE_ORDER[index]);
  setPipelineProgress((index + 0.15) / PIPELINE_ORDER.length);
  const result = await run();
  const duration_ms = Math.round(performance.now() - t0);
  await sleep(280);
  return { ...result, duration_ms };
}

async function doFullPipeline() {
  const file = getImportFile();
  if (!file) {
    setStatus("Seleccione un fichero CSV o cargue uno de referencia.", "error");
    setPipelineGuide("idle");
    return;
  }

  const btn = qs("#btnFullPipeline");
  const out = qs("#pipelineOut");
  const details = qs("#pipelineDetails");
  const card = qs("#pipelineCard");
  card?.classList.add("pipeline-hero-card--running");

  initPipelineSteps();
  showPipelineResults(false);
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Pipeline en marcha…";
  }
  if (details) details.hidden = true;
  if (out) out.textContent = "";

  const resultPayload = { steps: [], preview: null, import_result: null, aggregates: null, batch_id: null };
  const pipelineT0 = performance.now();

  try {
    // 1. Limpieza
    const preview = await runPipelineStep(0, file, async () => {
      const body = await importsApiJson("/imports/csv/preview?preview_limit=12", {
        method: "POST",
        body: formWithFile(file),
      });
      const q = body.quality_summary;
      let msg = `${body.total_rows} filas · ${(body.columns || []).length} columnas`;
      if (q) {
        msg += ` · completitud ${Math.round((q.completeness_ratio || 0) * 100)}%`;
        if (q.alerts?.length) msg += ` · ${q.alerts.length} alerta(s) detectada(s)`;
      }
      const st = q?.alerts?.length ? "warning" : "ok";
      return { status: st, message: msg, data: body };
    });
    patchPipelineStep(0, { status: preview.status, message: preview.message, duration_ms: preview.duration_ms });
    resultPayload.preview = preview.data;
    setPipelineProgress(0.25);

    // 2. Ingesta
    const ing = await runPipelineStep(1, file, async () => {
      const body = await importsApiJson("/imports/csv", { method: "POST", body: formWithFile(file) });
      const rows = body.batch?.row_count ?? "—";
      const msg = body.duplicate_file
        ? `Lote ya registrado (${rows} filas). Continuamos con transformación y análisis.`
        : body.message || `Importadas ${rows} filas.`;
      return { status: "ok", message: msg, data: body };
    });
    patchPipelineStep(1, { status: ing.status, message: ing.message, duration_ms: ing.duration_ms });
    resultPayload.import_result = ing.data;
    resultPayload.batch_id = ing.data?.batch?.batch_id || null;
    setPipelineProgress(0.5);

    // 3. Transformación
    const tx = await runPipelineStep(2, file, async () => {
      const body = await importsApiJson("/imports/csv/pipeline/transform", { method: "POST" });
      return {
        status: "ok",
        message: `Agregados: ${body.total_rows} filas en ${body.batches_with_rows} lote(s)`,
        data: body,
      };
    });
    patchPipelineStep(2, { status: tx.status, message: tx.message, duration_ms: tx.duration_ms });
    setPipelineProgress(0.75);

    // 4. Análisis
    const an = await runPipelineStep(3, file, async () => {
      const body = await importsApiJson("/stats/csv-aggregates?top=12");
      const s = body.summary || {};
      return {
        status: "ok",
        message: `Métricas listas: ${s.total_rows ?? 0} filas · ${s.batches_with_rows ?? 0} lotes`,
        data: body,
      };
    });
    patchPipelineStep(3, { status: an.status, message: an.message, duration_ms: an.duration_ms });
    resultPayload.aggregates = an.data;
    setPipelineProgress(0.85);

    let ml = { status: "warning", message: "Sin entrenar", data: null, duration_ms: 0 };
    try {
      ml = await runPipelineStep(4, file, async () => {
        const body = await importsApiJson("/ml/patient-disease/train", { method: "POST" });
        const mean = body.cv_accuracy_mean != null ? `${(body.cv_accuracy_mean * 100).toFixed(1)}%` : "—";
        return {
          status: "ok",
          message: `CV accuracy ${mean} · ${body.n_samples} muestras · ${body.n_classes} clases`,
          data: body,
        };
      });
      patchPipelineStep(4, { status: ml.status, message: ml.message, duration_ms: ml.duration_ms });
    } catch (mlErr) {
      const msg = String(mlErr.message || mlErr).slice(0, 180);
      patchPipelineStep(4, { status: "warning", message: msg });
      ml = { status: "warning", message: msg, data: null };
    }
    resultPayload.ml_metrics = ml.data;
    setPipelineProgress(1);

    renderSyncKpis(ing.data?.domain_sync);
    if (ml.data) renderMlKpis(ml.data);
    if (ing.data?.domain_sync || ml.data) showPipelineResults(true);

    resultPayload.steps = pipelineStepsState.map((s) => ({
      stage: s.stage,
      label: s.label,
      status: s.status,
      message: s.message,
      duration_ms: s.duration_ms,
    }));
    resultPayload.total_duration_ms = Math.round(performance.now() - pipelineT0);

    if (out) out.textContent = JSON.stringify(resultPayload, null, 2);
    if (details) details.hidden = false;

    setPipelineGuide("done");
    const dur = resultPayload.total_duration_ms;
    setStatus(`Pipeline completado en ${dur} ms. Puedes repetirlo con el mismo u otro CSV.`, "ok");

    await loadBatches();
    await loadSparkStats();
    if (resultPayload.batch_id) await loadDetail(resultPayload.batch_id);
  } catch (e) {
    const failedIdx = pipelineStepsState.findIndex((s) => s.status === "running");
    if (failedIdx >= 0) {
      patchPipelineStep(failedIdx, { status: "error", message: String(e.message || e).slice(0, 200) });
    }
    setPipelineGuide("idle");
    setStatus(String(e.message || e), "error");
    throw e;
  } finally {
    card?.classList.remove("pipeline-hero-card--running");
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Iniciar pipeline completo";
    }
  }
}

async function loadSampleCsv(url, label) {
  setStatus(`Cargando ${label}…`);
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`No se pudo descargar ${url}`);
  const blob = await res.blob();
  const name = url.split("/").pop() || "referencia.csv";
  const file = new File([blob], name, { type: blob.type || "text/csv" });
  setImportFile(file);
  initPipelineSteps();
  setPipelineGuide("idle");
  setStatus(`Listo: ${name}. Pulsa «Iniciar pipeline completo».`, "ok");
}

function wireSampleChips() {
  document.querySelectorAll(".csv-sample-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const url = btn.getAttribute("data-sample");
      const label = btn.textContent?.trim() || "CSV";
      if (!url) return;
      loadSampleCsv(url, label).catch((e) => setStatus(String(e.message || e), "error"));
    });
  });
}

async function doImport() {
  const file = getImportFile();
  if (!file) {
    setStatus("Seleccione un fichero CSV.", "error");
    return;
  }
  setStatus("Importando…");
  const fd = new FormData();
  fd.append("file", file, file.name);
  const body = await importsApiJson("/imports/csv", { method: "POST", body: fd });
  const el = qs("#importVisual");
  if (el) {
    const s = body.domain_sync || {};
    el.innerHTML = `
      <p class="imports-visual__lead">${escapeHtml(body.message)}</p>
      <div class="imports-kpi-row">
        <div class="imports-kpi"><span class="imports-kpi__val">${s.patients_created ?? 0}</span><span class="imports-kpi__lbl">Pacientes +</span></div>
        <div class="imports-kpi"><span class="imports-kpi__val">${s.patients_updated ?? 0}</span><span class="imports-kpi__lbl">Pacientes ↻</span></div>
        <div class="imports-kpi"><span class="imports-kpi__val">${s.medicos_created ?? 0}</span><span class="imports-kpi__lbl">Médicos +</span></div>
        <div class="imports-kpi"><span class="imports-kpi__val">${s.users_created ?? 0}</span><span class="imports-kpi__lbl">Usuarios +</span></div>
      </div>`;
    el.hidden = false;
  }
  setStatus(body.duplicate_file ? "Lote conocido; tablas clínicas actualizadas." : "Importación completada.", "ok");
  await loadBatches();
  await loadSparkStats();
}

/** @returns {Promise<boolean>} */
async function loadSparkStats() {
  const sum = qs("#sparkSummary");
  const tbody = qs("#sparkTopTbody");
  const empty = qs("#sparkEmpty");
  if (!sum || !tbody || !empty) return true;
  try {
    const body = await importsApiJson("/stats/csv-aggregates?top=12");
    const s = body.summary || {};
    sum.innerHTML = `
      <div class="imports-spark-kpis">
        <div><span class="imports-spark-kpi-label">Último cálculo</span><strong>${escapeHtml(fmtDate(s.computed_at))}</strong></div>
        <div><span class="imports-spark-kpi-label">Filas totales (agregado)</span><strong>${escapeHtml(String(s.total_rows ?? 0))}</strong></div>
        <div><span class="imports-spark-kpi-label">Lotes con datos</span><strong>${escapeHtml(String(s.batches_with_rows ?? 0))}</strong></div>
      </div>`;
    tbody.innerHTML = "";
    const tops = Array.isArray(body.top_batches) ? body.top_batches : [];
    if (tops.length === 0) {
      empty.hidden = false;
      return true;
    }
    empty.hidden = true;
    const max = Math.max(...tops.map((x) => Number(x.row_count) || 0), 1);
    for (const t of tops) {
      const rid = String(t.batch_id);
      const rc = Number(t.row_count) || 0;
      const pct = Math.max(4, Math.round((100 * rc) / max));
      const tr = document.createElement("tr");
      tr.innerHTML = `
      <td><code>${escapeHtml(rid)}</code></td>
      <td>${rc}</td>
      <td><div class="imports-spark-barwrap" aria-hidden="true"><div class="imports-spark-bar" style="width:${pct}%"></div></div></td>`;
      tbody.appendChild(tr);
    }
    return true;
  } catch (e) {
    tbody.innerHTML = "";
    empty.hidden = true;
    sum.textContent = `No se pudieron cargar las métricas Spark (${e.message || e}).`;
    return false;
  }
}

async function downloadBatchCsv(batchId) {
  const token = getToken();
  const url = `${API_BASE}/imports/csv/${batchId}/export`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`HTTP ${res.status}: ${t}`);
  }
  const blob = await res.blob();
  let name = `lote-${batchId.slice(0, 8)}.csv`;
  const cd = res.headers.get("Content-Disposition");
  if (cd) {
    const m = /filename="([^"]+)"/i.exec(cd);
    if (m) name = m[1];
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  URL.revokeObjectURL(a.href);
  a.remove();
}

async function loadBatches() {
  const token = getToken();
  const url = `${API_BASE}/imports/csv?limit=50&offset=0`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  const text = await res.text();
  const body = text ? JSON.parse(text) : [];
  if (!res.ok) throw new Error(text);
  const total = res.headers.get("X-Total-Count") || "—";
  qs("#batchTotal").textContent = total;
  const tbody = qs("#batchTbody");
  tbody.innerHTML = "";
  const empty = qs("#batchEmpty");
  if (!Array.isArray(body) || body.length === 0) {
    empty.hidden = false;
    return;
  }
  empty.hidden = true;
  for (const b of body) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${fmtDate(b.created_at)}</td>
      <td>${escapeHtml(b.source_filename || "—")}</td>
      <td>${b.row_count}</td>
      <td>${escapeHtml(b.ingest_status || "—")}</td>
      <td>
        <button type="button" class="imports-linkbtn" data-bid="${escapeHtml(b.batch_id)}">Ver</button>
        <button type="button" class="imports-linkbtn imports-linkbtn--secondary" data-dl="${escapeHtml(b.batch_id)}">CSV</button>
      </td>
    `;
    tbody.appendChild(tr);
  }
  tbody.querySelectorAll("[data-bid]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const bid = btn.getAttribute("data-bid");
      if (!bid) return;
      loadDetail(bid).catch((e) => setStatus(String(e.message || e), "error"));
    });
  });
  tbody.querySelectorAll("[data-dl]").forEach((btn) => {
    btn.addEventListener("click", () => {
      downloadBatchCsv(btn.getAttribute("data-dl")).catch((e) =>
        setStatus(String(e.message || e), "error"),
      );
    });
  });
}

function scrollToDetail() {
  const panel = qs("#sec-detail") || qs("#detailPanel") || qs("#detailOut");
  if (panel && panel.scrollIntoView) {
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function renderColumnFillBars(columnFill) {
  const entries = Object.entries(columnFill || {});
  if (!entries.length) return "<p class=\"imports-visual__meta\">Sin datos de columnas.</p>";
  return `<ul class="imports-fill-list">${entries
    .map(([col, pct]) => {
      const p = Math.round((pct || 0) * 100);
      return `<li class="imports-fill-row">
        <span class="imports-fill-row__label">${escapeHtml(col)}</span>
        <span class="imports-fill-row__bar"><span style="width:${p}%"></span></span>
        <span class="imports-fill-row__pct">${p}%</span>
      </li>`;
    })
    .join("")}</ul>`;
}

function renderQualityIssues(issues) {
  if (!issues?.length) return "<p class=\"imports-visual__meta\">Sin incidencias de calidad registradas.</p>";
  return `<ul class="imports-issue-list">${issues
    .map(
      (i) =>
        `<li><span class="imports-issue-sev">${escapeHtml(i.severity)}</span> ${escapeHtml(i.issue_type)} · ${escapeHtml(i.row_ref || "—")}</li>`,
    )
    .join("")}</ul>`;
}

async function loadDetail(batchId) {
  setStatus("Cargando detalle…");
  const el = qs("#detailVisual");
  const panel = qs("#sec-detail") || qs("#detailPanel");
  if (!el) return;
  el.innerHTML = "<p>Cargando…</p>";
  scrollToDetail();
  if (panel) panel.classList.add("imports-detail--active");
  try {
    const detail = await importsApiJson(`/imports/csv/${encodeURIComponent(batchId)}?rows_limit=40`);
    const cols = detail.columns || [];
    const rows = detail.rows || [];
    const q = detail.quality_summary;
    const sha = detail.sha256 ? `${detail.sha256.slice(0, 12)}…` : "—";
    const alerts =
      q?.alerts?.length ?
        `<ul class="imports-alert-list">${q.alerts.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}</ul>`
      : "";
    const head = cols.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
    const bodyRows = rows
      .map((r) => {
        const cells = cols.map((c) => `<td>${escapeHtml(String(r.fields?.[c] ?? ""))}</td>`).join("");
        return `<tr>${cells}</tr>`;
      })
      .join("");
    el.innerHTML = `
      <div class="imports-detail-head">
        <div>
          <h3 class="imports-detail-head__title">${escapeHtml(detail.source_filename || "Lote CSV")}</h3>
          <p class="imports-detail-head__sub"><code>${escapeHtml(batchId)}</code> · SHA ${escapeHtml(sha)}</p>
        </div>
        <div class="imports-kpi-row imports-kpi-row--compact">
          <div class="imports-kpi"><span class="imports-kpi__val">${detail.row_count}</span><span class="imports-kpi__lbl">Filas</span></div>
          <div class="imports-kpi"><span class="imports-kpi__val">${detail.rows_returned}</span><span class="imports-kpi__lbl">Mostradas</span></div>
          <div class="imports-kpi"><span class="imports-kpi__val">${detail.quality_issue_count ?? 0}</span><span class="imports-kpi__lbl">Incidencias</span></div>
          <div class="imports-kpi"><span class="imports-kpi__val">${detail.spark_row_count ?? "—"}</span><span class="imports-kpi__lbl">Agregado Spark</span></div>
        </div>
      </div>
      <div class="imports-detail-meta">
        <span class="imports-pill">${escapeHtml(detail.ingest_status || "—")}</span>
        <span class="imports-pill">${fmtDate(detail.created_at)}</span>
        ${q ? `<span class="imports-pill">Completitud ${Math.round((q.completeness_ratio || 0) * 100)}%</span>` : ""}
      </div>
      ${alerts}
      <section class="imports-detail-section"><h4>Completitud por columna</h4>${renderColumnFillBars(detail.column_fill)}</section>
      <section class="imports-detail-section"><h4>Incidencias (muestra)</h4>${renderQualityIssues(detail.sample_quality_issues)}</section>
      <section class="imports-detail-section"><h4>Filas del lote</h4>
        <div class="patients-table-wrap imports-table-scroll">
          <table class="data-table"><thead><tr>${head}</tr></thead><tbody>${bodyRows}</tbody></table>
        </div>
      </section>`;
    setStatus("Detalle del lote cargado.", "ok");
    scrollToDetail();
  } catch (e) {
    el.innerHTML = `<p class="imports-visual__error">${escapeHtml(String(e.message || e))}</p>`;
    setStatus(String(e.message || e), "error");
    scrollToDetail();
  }
}

function wireImportsUi() {
  qs("#filePreview")?.addEventListener("change", () => {
    const f = qs("#filePreview")?.files?.[0];
    if (f) setImportFile(f);
    else {
      importsSelectedFile = null;
      const hint = qs("#importsFileHint");
      if (hint) hint.textContent = "Seleccione un CSV o use un fichero de referencia.";
    }
    initPipelineSteps();
    setPipelineGuide(f ? "idle" : "idle");
    if (f) setStatus(`CSV «${f.name}» listo. Pulsa «Iniciar pipeline completo».`, "ok");
  });

  qs("#btnPreview")?.addEventListener("click", () =>
    doPreview().catch((e) => setStatus(String(e.message || e), "error")),
  );
  qs("#btnImport")?.addEventListener("click", () =>
    doImport().catch((e) => setStatus(String(e.message || e), "error")),
  );
  qs("#btnRefresh")?.addEventListener("click", () =>
    loadBatches().catch((e) => setStatus(String(e.message || e), "error")),
  );
  qs("#btnSparkRefresh")?.addEventListener("click", async () => {
    const ok = await loadSparkStats();
    setStatus(ok ? "Métricas Spark actualizadas." : "No se pudo actualizar métricas Spark.", ok ? "ok" : "error");
  });
  qs("#btnFullPipeline")?.addEventListener("click", () => {
    void doFullPipeline().catch((e) => {
      setStatus(String(e.message || e), "error");
      const btn = qs("#btnFullPipeline");
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Iniciar pipeline completo";
      }
    });
  });
  qs("#btnRetrainMl")?.addEventListener("click", () =>
    retrainMlModel().catch((e) => setMlStudioStatus(String(e.message || e), "error")),
  );
  qs("#btnRefreshMl")?.addEventListener("click", () =>
    loadMlStudio().catch((e) => setMlStudioStatus(String(e.message || e), "error")),
  );
  qs("#btnGoMlStudio")?.addEventListener("click", () => {
    const panel = qs("#mlStudioDetails");
    if (panel) panel.open = true;
    (panel || qs("#mlStudio"))?.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  wireSampleChips();
}

async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;
  const me = ctx.me;
  wireImportsUi();
  try {
    const sub = qs("#importsSub");
    if (sub) {
      sub.textContent = `Operaciones de ingesta · ${me.email} · ${ROLE_LABELS[me.role] || me.role}`;
    }
    initPipelineSteps();
    setPipelineGuide("idle");
    showPipelineResults(false);
    await loadBatches();
    const sparkOk = await loadSparkStats();
    loadMlStudio().catch((e) => setStatus(String(e.message || e), "error"));
    if (!sparkOk) setStatus("Métricas Spark no disponibles o API en error.", "error");
  } catch (e) {
    setStatus(String(e.message || e), "error");
    if (String(e.message || "").includes("401")) {
      setToken(null);
      redirectLogin();
    }
  }
}

boot();
