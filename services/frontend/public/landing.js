function apiBase() {
  const raw = window.API_BASE_URL || "/api";
  return String(raw).replace(/\/+$/, "");
}

const API_BASE = apiBase();

const qs = (s) => document.querySelector(s);

const subtitle = qs("#subtitle");
const emailEl = qs("#email");
const roleEl = qs("#role");
const idLabel = qs("#idLabel");
const idValue = qs("#idValue");
const statusEl = qs("#status");

const btnContinue = qs("#btnContinue");
const btnLogout = qs("#btnLogout");

function setStatus(message, kind = "neutral") {
  statusEl.textContent = message || "";
  statusEl.classList.remove("ok", "error");
  if (kind === "ok") statusEl.classList.add("ok");
  if (kind === "error") statusEl.classList.add("error");
}

function getToken() {
  return localStorage.getItem("access_token");
}

function setToken(token) {
  if (!token) localStorage.removeItem("access_token");
  else localStorage.setItem("access_token", token);
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
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

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

function redirectToLogin() {
  window.location.href = "/index.html";
}

btnContinue.addEventListener("click", () => {
  window.location.href = "/index.html?noredirect=1";
});

btnLogout.addEventListener("click", () => {
  setToken(null);
  redirectToLogin();
});

async function boot() {
  const token = getToken();
  if (!token) {
    redirectToLogin();
    return;
  }

  try {
    const me = await api("/auth/me");
    subtitle.textContent = "Tu sesión está activa.";
    emailEl.textContent = me.email || "—";
    roleEl.textContent = me.role || "—";
    if (me.role === "paciente") {
      idLabel.textContent = "ID paciente";
      idValue.textContent = me.patient_id || "—";
    } else if (me.role === "medico") {
      idLabel.textContent = "ID médico";
      idValue.textContent = me.medico_id || "—";
    } else {
      idLabel.textContent = "Cuenta";
      idValue.textContent = "—";
    }
    setStatus("");
  } catch (e) {
    setStatus(String(e.message || e), "error");
    subtitle.textContent = "No se pudo validar la sesión.";
    setToken(null);
  }
}

boot();
