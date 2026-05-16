/** Utilidades compartidas del portal laSalle Health Center */
function apiBase() {
  const raw = window.API_BASE_URL || "/api";
  return String(raw).replace(/\/+$/, "");
}

const PORTAL_API_BASE = apiBase();

const ROLE_LABELS = {
  paciente: "Paciente",
  medico: "Médico / personal clínico",
  admin: "Administración",
};

function portalQs(s) {
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

function redirectLogin() {
  window.location.href = "/index.html";
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

async function apiJson(path, opts = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const url = `${PORTAL_API_BASE}${path}`;
  let res;
  try {
    res = await fetch(url, Object.assign({}, opts, { headers }));
  } catch (e) {
    const name = e && e.name ? e.name : "Error";
    const msg = e && e.message ? e.message : String(e);
    throw new Error(`Red: ${name}: ${msg}`);
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
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }
  return body;
}

function setPageStatus(msg, kind = "neutral") {
  const el = portalQs("#status");
  if (!el) return;
  el.textContent = msg || "";
  el.classList.remove("ok", "error");
  if (kind === "ok") el.classList.add("ok");
  if (kind === "error") el.classList.add("error");
}

function wireLogout() {
  const btn = portalQs("#btnLogout");
  if (!btn) return;
  btn.addEventListener("click", () => {
    setToken(null);
    redirectLogin();
  });
}

async function requireAuth() {
  const token = getToken();
  if (!token) {
    redirectLogin();
    return null;
  }
  try {
    return await apiJson("/auth/me");
  } catch {
    setToken(null);
    redirectLogin();
    return null;
  }
}

function deriveDisplayName(me) {
  const email = (me && me.email) || "";
  const local = email.includes("@") ? email.split("@")[0] : email;
  if (!local) return "—";
  return local.charAt(0).toUpperCase() + local.slice(1);
}

function formatDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(d);
}

function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return new Intl.DateTimeFormat("es-ES", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}
