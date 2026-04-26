function apiBase() {
  const raw = window.API_BASE_URL || "/api";
  return String(raw).replace(/\/+$/, "");
}

const API_BASE = apiBase();

const qs = (s) => document.querySelector(s);
const qsa = (s) => document.querySelectorAll(s);

const userNameEl = qs("#userName");
const avatarInitialsEl = qs("#avatarInitials");
const dashSubEl = qs("#dashSub");
const chipRoleEl = qs("#chipRole");
const chipIdEl = qs("#chipId");
const statusEl = qs("#status");

const mNextAppt = qs("#mNextAppt");
const mNextApptHint = qs("#mNextApptHint");
const mSecondaryLabel = qs("#mSecondaryLabel");
const mSecondaryValue = qs("#mSecondaryValue");
const mSecondaryHint = qs("#mSecondaryHint");
const mNotif = qs("#mNotif");

const actionsSub = qs("#actionsSub");
const actionAppointmentsTitle = qs("#actionAppointmentsTitle");
const actionRecordsTitle = qs("#actionRecordsTitle");
const actionsList = qs("#actionsList");

const loginMeta = qs("#loginMeta");

const ROLE_LABELS = {
  paciente: "Paciente",
  medico: "Médico / personal clínico",
  admin: "Administración",
};

function setStatus(message, kind = "neutral") {
  if (!statusEl) return;
  statusEl.textContent = message || "";
  statusEl.classList.remove("ok", "error");
  if (kind === "ok") statusEl.classList.add("ok");
  if (kind === "error") statusEl.classList.add("error");
}

function getToken() {
  return (
    localStorage.getItem("access_token") ||
    sessionStorage.getItem("access_token") ||
    null
  );
}

function setToken(token) {
  if (!token) {
    localStorage.removeItem("access_token");
    sessionStorage.removeItem("access_token");
    return;
  }
  localStorage.setItem("access_token", token);
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

const btnLogout = qs("#btnLogout");
if (btnLogout) {
  btnLogout.addEventListener("click", () => {
    setToken(null);
    redirectToLogin();
  });
}

if (actionsList) {
  actionsList.addEventListener("click", (e) => {
    const a = e.target.closest("[data-action]");
    if (!a) return;
    e.preventDefault();
    const action = a.getAttribute("data-action");
    setStatus(`"${a.querySelector(".action__title")?.textContent || action}" estará disponible próximamente.`, "ok");
  });
}

function deriveDisplayName(me) {
  const email = (me && me.email) || "";
  const local = email.includes("@") ? email.split("@")[0] : email;
  if (!local) return "—";
  return local.charAt(0).toUpperCase() + local.slice(1);
}

function deriveInitials(name) {
  if (!name || name === "—") return "·";
  const cleaned = String(name).replace(/[^A-Za-z\u00C0-\u017F]+/g, " ").trim();
  if (!cleaned) return "·";
  const parts = cleaned.split(/\s+/).slice(0, 2);
  return parts.map((p) => p.charAt(0).toUpperCase()).join("") || cleaned.charAt(0).toUpperCase();
}

function applyRoleSpecifics(me) {
  const role = me.role;

  if (role === "paciente") {
    chipRoleEl.textContent = ROLE_LABELS.paciente;
    chipRoleEl.classList.add("chip--brand");
    chipIdEl.textContent = me.patient_id ? `ID paciente · ${me.patient_id}` : "Sin ID asignado";
    actionsSub.textContent = "Acciones disponibles para pacientes.";
    actionAppointmentsTitle.textContent = "Mis citas";
    actionRecordsTitle.textContent = "Mi expediente";
    mSecondaryLabel.textContent = "Última visita";
    mSecondaryValue.textContent = "—";
    mSecondaryHint.textContent = "Aún sin registros clínicos.";
    return;
  }

  if (role === "medico") {
    chipRoleEl.textContent = ROLE_LABELS.medico;
    chipRoleEl.classList.add("chip--brand");
    chipIdEl.textContent = me.medico_id ? `ID médico · ${me.medico_id}` : "Sin ID asignado";
    actionsSub.textContent = "Acciones disponibles para personal clínico.";
    actionAppointmentsTitle.textContent = "Agenda del día";
    actionRecordsTitle.textContent = "Pacientes asignados";
    mSecondaryLabel.textContent = "Pacientes asignados";
    mSecondaryValue.textContent = "—";
    mSecondaryHint.textContent = "Sin información agregada todavía.";
    return;
  }

  chipRoleEl.textContent = ROLE_LABELS.admin;
  chipRoleEl.classList.add("chip--brand");
  chipIdEl.textContent = "Cuenta administradora";
  actionsSub.textContent = "Acciones disponibles para administración.";
  actionAppointmentsTitle.textContent = "Calendario operativo";
  actionRecordsTitle.textContent = "Gestión de usuarios";
  mSecondaryLabel.textContent = "Usuarios activos";
  mSecondaryValue.textContent = "—";
  mSecondaryHint.textContent = "Disponible al conectar el endpoint.";
}

function setLoginMeta() {
  const now = new Date();
  const fmt = new Intl.DateTimeFormat("es-ES", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  });
  loginMeta.textContent = `Acceso correcto · ${fmt.format(now)}`;
}

async function boot() {
  const token = getToken();
  if (!token) {
    redirectToLogin();
    return;
  }

  try {
    const me = await api("/auth/me");
    const display = deriveDisplayName(me);
    userNameEl.textContent = display;
    if (avatarInitialsEl) avatarInitialsEl.textContent = deriveInitials(display);
    dashSubEl.textContent = me.email
      ? `Sesión activa · ${me.email}`
      : "Sesión activa.";
    applyRoleSpecifics(me);
    setLoginMeta();
    mNextAppt.textContent = "—";
    mNextApptHint.textContent = "Sin citas programadas en este momento.";
    mNotif.textContent = "0";
    setStatus("");
  } catch (e) {
    userNameEl.textContent = "—";
    dashSubEl.textContent = "No se pudo validar la sesión. Vuelve a identificarte en el acceso al portal.";
    setStatus(String(e.message || e), "error");
    setToken(null);
  }
}

boot();
