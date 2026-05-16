function setRxStatus(msg, kind = "neutral") {
  const el = portalQs("#status");
  if (!el) return;
  el.textContent = msg || "";
  el.classList.remove("ok", "error", "clinic-alert--ok", "clinic-alert--error");
  if (kind === "ok") el.classList.add("ok", "clinic-alert--ok");
  if (kind === "error") el.classList.add("error", "clinic-alert--error");
}

async function loadMetrics() {
  const pre = portalQs("#metricsOut");
  try {
    const body = await apiJson("/radiology/metrics");
    pre.textContent = JSON.stringify(body, null, 2);
    setRxStatus("Métricas del modelo cargadas.", "ok");
  } catch (e) {
    pre.textContent = String(e.message || e);
    setRxStatus("No se pudieron cargar las métricas.", "error");
  }
}

async function doPredict() {
  const input = portalQs("#fileRx");
  const file = input.files && input.files[0];
  if (!file) {
    setRxStatus("Seleccione una imagen PNG o JPEG.", "error");
    return;
  }
  setRxStatus("Calculando predicción…");
  const token = getToken();
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const fd = new FormData();
  fd.append("file", file, file.name);
  const res = await fetch(`${PORTAL_API_BASE}/radiology/predict`, { method: "POST", headers, body: fd });
  const text = await res.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  const out = portalQs("#predictOut");
  out.hidden = false;
  if (!res.ok) {
    const msg =
      typeof body === "string"
        ? body
        : body && body.detail
          ? typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail)
          : JSON.stringify(body);
    out.textContent = `Error HTTP ${res.status}: ${msg}`;
    setRxStatus("Fallo en la predicción.", "error");
    return;
  }
  out.textContent = JSON.stringify(body, null, 2);
  setRxStatus("Predicción completada. Revise el resultado con criterio clínico.", "ok");
}

(async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;
  const { me } = ctx;

  const sub = portalQs("#rxSub");
  if (sub) {
    sub.innerHTML =
      `Analice imágenes RX en segundos. Clases: <strong>Sana</strong>, <strong>Neumonía</strong> y <strong>COVID-19</strong>. ` +
      `Sesión: ${me.email} · ${ROLE_LABELS[me.role]}.`;
  }

  const fileInput = portalQs("#fileRx");
  const hint = portalQs("#rxFileHint");
  if (fileInput && hint) {
    fileInput.addEventListener("change", () => {
      const file = fileInput.files && fileInput.files[0];
      if (file) hint.textContent = file.name;
    });
  }

  portalQs("#btnPredict").addEventListener("click", () => void doPredict());
  await loadMetrics();
})();
