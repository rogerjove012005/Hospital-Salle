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
  if (token) headers.Authorization = `Bearer ${token}`;
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

async function loadMetrics() {
  const pre = qs("#metricsOut");
  try {
    const { body } = await apiJson("/radiology/metrics");
    pre.textContent = JSON.stringify(body, null, 2);
    setStatus("Métricas cargadas.", "ok");
  } catch (e) {
    pre.textContent = String(e.message || e);
    setStatus("No se pudieron cargar métricas (¿sesión válida?).", "error");
  }
}

async function doPredict() {
  const input = qs("#fileRx");
  const file = input.files && input.files[0];
  if (!file) {
    setStatus("Seleccione una imagen PNG o JPEG.", "error");
    return;
  }
  setStatus("Calculando predicción…");
  const token = getToken();
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const fd = new FormData();
  fd.append("file", file, file.name);
  const res = await fetch(`${API_BASE}/radiology/predict`, { method: "POST", headers, body: fd });
  const text = await res.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  const out = qs("#predictOut");
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
    setStatus("Fallo en predicción.", "error");
    return;
  }
  out.textContent = JSON.stringify(body, null, 2);
  setStatus("Predicción lista.", "ok");
}

async function boot() {
  const token = getToken();
  if (!token) {
    redirectLogin();
    return;
  }
  try {
    const { body } = await apiJson("/auth/me");
    const sub = qs("#rxSub");
    if (sub) {
      sub.textContent =
        `${sub.textContent} · Sesión: ${body.email || "—"} · Rol: ${body.role}`;
    }
  } catch (_) {
    setToken(null);
    redirectLogin();
    return;
  }

  qs("#btnLogout").addEventListener("click", () => {
    setToken(null);
    redirectLogin();
  });

  const fileInput = qs("#fileRx");
  const dropzone = fileInput && fileInput.closest(".rx-dropzone");
  if (fileInput && dropzone) {
    fileInput.addEventListener("change", () => {
      const file = fileInput.files && fileInput.files[0];
      const hint = dropzone.querySelector(".rx-dropzone__hint");
      if (hint && file) hint.textContent = file.name;
    });
  }

  qs("#btnPredict").addEventListener("click", () => {
    void doPredict();
  });

  await loadMetrics();
}

boot();
