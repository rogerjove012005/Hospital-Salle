function apiBase() {
  const raw = window.API_BASE_URL || "/api";
  return String(raw).replace(/\/+$/, "");
}

const API_BASE = apiBase();

function qs(s) {
  return document.querySelector(s);
}

function getToken() {
  return localStorage.getItem("access_token") || sessionStorage.getItem("access_token") || null;
}

function setToken(t) {
  if (!t) {
    localStorage.removeItem("access_token");
    sessionStorage.removeItem("access_token");
    return;
  }
  localStorage.setItem("access_token", t);
}

function setStatus(msg, kind = "neutral") {
  const el = qs("#status");
  if (!el) return;
  el.textContent = msg || "";
  el.classList.remove("ok", "error");
  if (kind === "ok") el.classList.add("ok");
  if (kind === "error") el.classList.add("error");
}

function redirectLogin() {
  window.location.href = "/index.html";
}

async function apiJson(path, opts = {}) {
  const headers = Object.assign({}, opts.headers || {});
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, Object.assign({}, opts, { headers }));
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
  return { res, body };
}

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES");
  } catch {
    return String(iso);
  }
}

async function doPreview() {
  const input = qs("#filePreview");
  const file = input.files && input.files[0];
  if (!file) {
    setStatus("Seleccione un fichero CSV.", "error");
    return;
  }
  setStatus("Generando vista previa…");
  const fd = new FormData();
  fd.append("file", file, file.name);
  const { body } = await apiJson("/imports/csv/preview?preview_limit=15", { method: "POST", body: fd });
  const pre = qs("#previewOut");
  pre.hidden = false;
  pre.textContent = JSON.stringify(body, null, 2);
  setStatus("Vista previa lista.", "ok");
}

async function doImport() {
  const input = qs("#fileImport");
  const file = input.files && input.files[0];
  if (!file) {
    setStatus("Seleccione un fichero CSV.", "error");
    return;
  }
  setStatus("Importando…");
  const fd = new FormData();
  fd.append("file", file, file.name);
  const { body } = await apiJson("/imports/csv", { method: "POST", body: fd });
  const pre = qs("#importOut");
  pre.hidden = false;
  pre.textContent = JSON.stringify(body, null, 2);
  setStatus(body.duplicate_file ? "Lote ya existía (mismo contenido)." : "Importación completada.", "ok");
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
    const { body } = await apiJson("/stats/csv-aggregates?top=12");
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
    btn.addEventListener("click", () => loadDetail(btn.getAttribute("data-bid")));
  });
  tbody.querySelectorAll("[data-dl]").forEach((btn) => {
    btn.addEventListener("click", () => {
      downloadBatchCsv(btn.getAttribute("data-dl")).catch((e) =>
        setStatus(String(e.message || e), "error"),
      );
    });
  });
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function loadDetail(batchId) {
  setStatus("Cargando detalle…");
  const pre = qs("#detailOut");
  try {
    const { body: detail } = await apiJson(`/imports/csv/${batchId}?rows_limit=30`);
    let issues = [];
    try {
      const { body: q } = await apiJson(`/imports/csv/${batchId}/quality-issues?limit=50`);
      issues = q;
    } catch {
      issues = [];
    }
    pre.textContent = JSON.stringify({ detalle: detail, quality_issues: issues }, null, 2);
    setStatus("Detalle cargado.", "ok");
  } catch (e) {
    pre.textContent = String(e.message || e);
    setStatus(String(e.message || e), "error");
  }
}

async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;
  const me = ctx.me;
  try {
    qs("#importsSub").textContent = `Operaciones de ingesta · ${me.email} · ${ROLE_LABELS[me.role] || me.role}`;
    await loadBatches();
    const sparkOk = await loadSparkStats();
    if (!sparkOk) setStatus("Métricas Spark no disponibles o API en error.", "error");
  } catch (e) {
    setStatus(String(e.message || e), "error");
    if (String(e.message || "").includes("401")) {
      setToken(null);
      redirectLogin();
    }
  }
}

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

boot();
