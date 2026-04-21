const API_BASE = window.API_BASE_URL || "http://localhost:8000";

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

async function api(path, opts = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, Object.assign({}, opts, { headers }));
  const text = await res.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    const msg = typeof body === "string" ? body : (body && body.detail) ? body.detail : JSON.stringify(body);
    throw new Error(msg);
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
  if (isLogin) {
    qs("h1").textContent = "Iniciar sesión";
    qs(".header .muted").textContent = "Accede a tu cuenta para continuar.";
  } else {
    qs("h1").textContent = "Crear cuenta";
    qs(".header .muted").textContent = "Registra tu cuenta de paciente.";
  }
}

tabLogin.addEventListener("click", () => setTab("login"));
tabRegister.addEventListener("click", () => setTab("register"));

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
    setStatus("Sesión iniciada.", "ok");
    sessionPanel.classList.remove("hidden");
  } catch (err) {
    setStatus(String(err.message || err), "error");
  }
});

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(registerForm);
  const email = form.get("email");
  const password = form.get("password");
  const patient_id = form.get("patient_id");

  try {
    setStatus("Creando cuenta…");
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, patient_id }),
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

  if (getToken()) {
    sessionPanel.classList.remove("hidden");
  }
}

boot();
