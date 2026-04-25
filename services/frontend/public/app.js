function apiBase() {
  const raw = window.API_BASE_URL || "/api";
  return String(raw).replace(/\/+$/, "");
}

const API_BASE = apiBase();

const qs = (s) => document.querySelector(s);
const output = qs("#output");
const statusEl = qs("#status");
const sessionPanel = qs("#sessionPanel");

const tabLogin = qs("#tabLogin");
const tabRegister = qs("#tabRegister");
const panelLogin = qs("#panelLogin");
const panelRegister = qs("#panelRegister");

const loginForm = qs("#loginForm");
const registerForm = qs("#registerForm");

const btnMe = qs("#btnMe");
const btnLogout = qs("#btnLogout");

const linkForgot = qs("#linkForgot");
const forgotModal = qs("#forgotModal");
const forgotForm = qs("#forgotForm");
const forgotEmail = qs("#forgot-email");
const forgotStatus = qs("#forgotStatus");

function setForgotStatus(message, kind = "neutral") {
  if (!forgotStatus) return;
  forgotStatus.textContent = message || "";
  forgotStatus.classList.remove("ok", "error");
  if (kind === "ok") forgotStatus.classList.add("ok");
  if (kind === "error") forgotStatus.classList.add("error");
}

function isModalOpen() {
  return forgotModal && !forgotModal.classList.contains("hidden");
}

function openForgotModal(prefillEmail) {
  if (!forgotModal) return;
  forgotModal.classList.remove("hidden");
  setForgotStatus("");
  if (forgotEmail) {
    if (prefillEmail !== null && prefillEmail !== undefined) {
      const v = String(prefillEmail);
      if (v && v !== "undefined" && v !== "null") forgotEmail.value = v;
    }
    setTimeout(() => forgotEmail.focus(), 0);
  }
  document.body.style.overflow = "hidden";
}

function closeForgotModal() {
  if (!forgotModal) return;
  forgotModal.classList.add("hidden");
  setForgotStatus("");
  document.body.style.overflow = "";
}

function shouldSkipLandingRedirect() {
  return new URLSearchParams(window.location.search).get("noredirect") === "1";
}

function goToLanding() {
  window.location.href = "/landing.html";
}

function setOutput(obj) {
  output.textContent = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
}

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

function setTab(which) {
  const isLogin = which === "login";
  tabLogin.classList.toggle("active", isLogin);
  tabRegister.classList.toggle("active", !isLogin);
  panelLogin.classList.toggle("hidden", !isLogin);
  panelRegister.classList.toggle("hidden", isLogin);
  setStatus("");
  const title = qs("#pageTitle");
  const sub = qs("#pageSubtitle");
  const kicker = qs("#formKicker");
  if (isLogin) {
    if (title) title.textContent = "Iniciar sesión";
    if (sub)
      sub.textContent =
        "Use el correo y la contraseña de su cuenta en laSalle Health Center.";
    if (kicker) kicker.textContent = "Acceso de usuarios registrados";
  } else {
    if (title) title.textContent = "Alta de usuario";
    if (sub)
      sub.textContent =
        "Complete los datos para registrarse como paciente o personal. Se generarán los identificadores de expediente según el perfil.";
    if (kicker) kicker.textContent = "Nuevo usuario — laSalle Health Center";
  }
  if (tabLogin) tabLogin.setAttribute("aria-selected", isLogin ? "true" : "false");
  if (tabRegister) tabRegister.setAttribute("aria-selected", isLogin ? "false" : "true");
}

tabLogin.addEventListener("click", () => setTab("login"));
tabRegister.addEventListener("click", () => setTab("register"));

if (linkForgot) {
  linkForgot.addEventListener("click", (e) => {
    e.preventDefault();
    const loginEmail = qs("#login-email");
    openForgotModal(loginEmail && typeof loginEmail.value === "string" ? loginEmail.value : "");
  });
}

// Defensive: some desktop browsers/extensions can interfere with direct listeners on anchors.
// Delegation ensures the modal still opens reliably.
document.addEventListener(
  "click",
  (e) => {
    const t = e.target;
    if (!t) return;
    const el = t.closest ? t.closest("#linkForgot") : null;
    if (!el) return;
    e.preventDefault();
    const loginEmail = qs("#login-email");
    openForgotModal(loginEmail && typeof loginEmail.value === "string" ? loginEmail.value : "");
  },
  true
);

if (forgotModal) {
  forgotModal.addEventListener("click", (e) => {
    const t = e.target;
    if (t && t.getAttribute && t.getAttribute("data-modal-close") === "true") {
      closeForgotModal();
    }
  });
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && isModalOpen()) closeForgotModal();
});

if (forgotForm) {
  forgotForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = new FormData(forgotForm);
    const email = form.get("email");
    try {
      setForgotStatus("Enviando…");
      await api("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setForgotStatus(
        "Listo. Si el correo está registrado, recibirá un enlace para restablecer la contraseña.",
        "ok"
      );
    } catch (err) {
      setForgotStatus(String(err.message || err), "error");
    }
  });
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(loginForm);
  const email = form.get("email");
  const password = form.get("password");

  try {
    setStatus("Entrando…");
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    goToLanding();
  } catch (err) {
    setStatus(String(err.message || err), "error");
  }
});

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(registerForm);
  const role = form.get("role");
  const first_name = form.get("first_name");
  const last_name = form.get("last_name");
  const phone = form.get("phone");
  const date_of_birth = form.get("date_of_birth");
  const sex = form.get("sex");
  const email = form.get("email");
  const password = form.get("password");

  try {
    setStatus("Creando cuenta…");
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        role,
        first_name,
        last_name,
        phone,
        date_of_birth,
        sex,
      }),
    });
    setStatus("Cuenta creada. Ya puedes iniciar sesión.", "ok");
    setTab("login");
  } catch (err) {
    setStatus(String(err.message || err), "error");
  }
});

btnMe.addEventListener("click", async () => {
  try {
    const me = await api("/auth/me");
    output.classList.remove("hidden");
    setOutput(me);
  } catch (err) {
    setStatus(String(err.message || err), "error");
  }
});

btnLogout.addEventListener("click", () => {
  setToken(null);
  output.classList.add("hidden");
  setOutput("{}");
  sessionPanel.classList.add("hidden");
  setStatus("Sesión cerrada.", "ok");
});

async function boot() {
  try {
    await api("/health");
    // ok
  } catch {
    setStatus("No se puede conectar con el servidor.", "error");
  }

  if (getToken() && !shouldSkipLandingRedirect()) {
    goToLanding();
    return;
  }

  if (getToken()) {
    sessionPanel.classList.remove("hidden");
  }
}

boot();
