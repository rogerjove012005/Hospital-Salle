function apiBase() {
  const raw = window.API_BASE_URL || "/api";
  return String(raw).replace(/\/+$/, "");
}

const API_BASE = apiBase();
const qs = (s) => document.querySelector(s);

const resetForm = qs("#resetForm");
const statusEl = qs("#status");

function setStatus(message, kind = "neutral") {
  statusEl.textContent = message || "";
  statusEl.classList.remove("ok", "error");
  if (kind === "ok") statusEl.classList.add("ok");
  if (kind === "error") statusEl.classList.add("error");
}

function formatApiDetail(detail) {
  if (!detail) return "Error desconocido";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const loc = Array.isArray(d.loc) ? d.loc.filter((x) => x !== "body").join(".") : "";
        const msg = d.msg || "";
        return loc ? `${loc}: ${msg}` : msg;
      })
      .filter(Boolean)
      .join("\n");
  }
  return JSON.stringify(detail);
}

async function api(path, opts = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
  const url = `${API_BASE}${path}`;
  let res;
  try {
    res = await fetch(url, Object.assign({}, opts, { headers }));
  } catch (e) {
    const name = e && e.name ? e.name : "Error";
    const msg = e && e.message ? e.message : String(e);
    throw new Error(`Red: ${name}: ${msg} (url=${url})`);
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
        : body && Object.prototype.hasOwnProperty.call(body, "detail")
          ? formatApiDetail(body.detail)
          : JSON.stringify(body);
    throw new Error(`HTTP ${res.status}: ${msg} (url=${url})`);
  }
  return body;
}

function getTokenFromUrl() {
  return new URLSearchParams(window.location.search).get("token") || "";
}

async function boot() {
  const token = getTokenFromUrl();
  if (!token) {
    setStatus("Falta el token. Use el enlace enviado por el sistema.", "error");
  }
}

resetForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const token = getTokenFromUrl();
  if (!token) {
    setStatus("Falta el token. Use el enlace enviado por el sistema.", "error");
    return;
  }

  const form = new FormData(resetForm);
  const p1 = String(form.get("new_password") || "");
  const p2 = String(form.get("new_password_2") || "");
  if (p1 !== p2) {
    setStatus("Las contraseñas no coinciden.", "error");
    return;
  }

  try {
    setStatus("Actualizando…");
    await api("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: p1 }),
    });
    setStatus("Contraseña actualizada. Ya puede iniciar sesión.", "ok");
    setTimeout(() => {
      window.location.href = "/index.html";
    }, 800);
  } catch (err) {
    setStatus(String(err.message || err), "error");
  }
});

boot();

