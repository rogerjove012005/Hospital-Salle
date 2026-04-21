const API_BASE = window.API_BASE_URL || "http://localhost:8000";

const qs = (s) => document.querySelector(s);
const output = qs("#output");
const apiStatus = qs("#apiStatus");

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
    throw new Error(typeof body === "string" ? body : JSON.stringify(body));
  }
  return body;
}

function setTab(which) {
  const isLogin = which === "login";
  tabLogin.classList.toggle("active", isLogin);
  tabRegister.classList.toggle("active", !isLogin);
  panelLogin.classList.toggle("hidden", !isLogin);
  panelRegister.classList.toggle("hidden", isLogin);
}

tabLogin.addEventListener("click", () => setTab("login"));
tabRegister.addEventListener("click", () => setTab("register"));

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(loginForm);
  const email = form.get("email");
  const password = form.get("password");

  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    setOutput({ ok: true, action: "login", token_saved: true });
  } catch (err) {
    setOutput({ ok: false, action: "login", error: String(err.message || err) });
  }
});

registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(registerForm);
  const email = form.get("email");
  const password = form.get("password");
  const patient_id = form.get("patient_id");

  try {
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, patient_id }),
    });
    setOutput({ ok: true, action: "register", user: data });
  } catch (err) {
    setOutput({ ok: false, action: "register", error: String(err.message || err) });
  }
});

btnMe.addEventListener("click", async () => {
  try {
    const me = await api("/auth/me");
    setOutput({ ok: true, me });
  } catch (err) {
    setOutput({ ok: false, error: String(err.message || err) });
  }
});

btnLogout.addEventListener("click", () => {
  setToken(null);
  setOutput({ ok: true, action: "logout" });
});

async function boot() {
  try {
    await api("/health");
    apiStatus.textContent = "API: OK";
    apiStatus.style.borderColor = "rgba(47, 224, 143, 0.55)";
  } catch {
    apiStatus.textContent = "API: OFF";
    apiStatus.style.borderColor = "rgba(255, 92, 122, 0.55)";
  }
}

boot();
