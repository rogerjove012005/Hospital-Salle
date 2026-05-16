/** Portal clínico laSalle — auth, permisos y chrome compartido */
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

const ROLE_LABELS_SHORT = {
  paciente: "Paciente",
  medico: "Médico",
  admin: "Admin",
};

/** Páginas y roles permitidos */
const PORTAL_PAGES = {
  dashboard: { roles: ["paciente", "medico", "admin"] },
  profile: { roles: ["paciente", "medico", "admin"] },
  agenda: { roles: ["paciente", "medico", "admin"] },
  records: { roles: ["paciente"] },
  patients: { roles: ["medico", "admin"] },
  radiology: { roles: ["medico", "admin"] },
  imports: { roles: ["medico", "admin"] },
  contact: { roles: ["paciente", "medico", "admin"] },
};

function agendaLabel(role) {
  if (role === "medico") return "Agenda del día";
  if (role === "admin") return "Calendario operativo";
  return "Mis citas";
}

function recordsLabel(role) {
  if (role === "paciente") return "Mi expediente";
  if (role === "medico") return "Pacientes asignados";
  return "Directorio de pacientes";
}

function buildNavSections(role) {
  const sections = [
    {
      title: "Inicio",
      items: [{ id: "dashboard", href: "/landing.html", label: "Mi panel" }],
    },
    {
      title: "Área personal",
      items: [
        { id: "profile", href: "/profile.html", label: "Mi perfil" },
        { id: "agenda", href: "/agenda.html", label: agendaLabel(role) },
      ],
    },
  ];

  if (role === "paciente") {
    sections[1].items.push({ id: "records", href: "/records.html", label: "Mi expediente" });
  }
  if (role === "medico" || role === "admin") {
    sections[1].items.push({
      id: "patients",
      href: "/patients.html",
      label: role === "admin" ? "Directorio de pacientes" : "Pacientes asignados",
    });
  }

  const clinica = {
    title: "Clínica e inteligencia artificial",
    items: [],
  };
  if (role === "medico" || role === "admin") {
    clinica.items.push({
      id: "radiology",
      href: "/radiology.html",
      label: "Radiología asistida (RX)",
      featured: true,
    });
  }
  if (clinica.items.length) sections.push(clinica);

  if (role === "medico" || role === "admin") {
    sections.push({
      title: "Operaciones hospitalarias",
      items: [{ id: "imports", href: "/imports.html", label: "Ingesta CSV" }],
    });
  }

  sections.push({
    title: "Atención al usuario",
    items: [{ id: "contact", href: "/contact.html", label: "Contacto y soporte" }],
  });

  return sections;
}

function canAccessPage(role, pageId) {
  const page = PORTAL_PAGES[pageId];
  return page ? page.roles.includes(role) : true;
}

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
  el.classList.remove("ok", "error", "clinic-alert--ok", "clinic-alert--error");
  if (kind === "ok") {
    el.classList.add("ok", "clinic-alert--ok");
  }
  if (kind === "error") {
    el.classList.add("error", "clinic-alert--error");
  }
}

function deriveDisplayName(me, detail) {
  if (detail && detail.full_name) return detail.full_name;
  const email = (me && me.email) || "";
  const local = email.includes("@") ? email.split("@")[0] : email;
  if (!local) return "Usuario";
  return local.charAt(0).toUpperCase() + local.slice(1);
}

function deriveInitials(name) {
  if (!name || name === "—") return "·";
  const cleaned = String(name).replace(/[^A-Za-z\u00C0-\u017F]+/g, " ").trim();
  if (!cleaned) return "·";
  const parts = cleaned.split(/\s+/).slice(0, 2);
  return parts.map((p) => p.charAt(0).toUpperCase()).join("") || cleaned.charAt(0).toUpperCase();
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

function roleIdChip(me) {
  if (me.role === "paciente") {
    return me.patient_id ? `ID paciente · ${me.patient_id}` : "Sin ficha clínica";
  }
  if (me.role === "medico") {
    return me.medico_id ? `ID médico · ${me.medico_id}` : "Sin ficha profesional";
  }
  return "Cuenta de administración";
}

const NAV_ICONS = {
  dashboard:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 11h6V4H4v7zm10 9h6v-7h-6v7zM4 20h6v-5H4v5zm10-9h6V4h-6v7z"/></svg>',
  profile:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-7 8-7s8 3 8 7"/></svg>',
  agenda:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 9h18M8 3v4M16 3v4"/></svg>',
  records:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/></svg>',
  patients:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M17 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
  radiology:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 9h6M7 13h10"/></svg>',
  imports:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v12M8 11l4 4 4-4"/><path d="M4 15v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/></svg>',
  contact:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 11.5a8.4 8.4 0 0 1-1 4 8.5 8.5 0 0 1-7.5 4.5 8.4 8.4 0 0 1-4-1L3 21l2-5.5a8.4 8.4 0 0 1-1-4 8.5 8.5 0 0 1 4.5-7.5 8.4 8.4 0 0 1 4-1 8.5 8.5 0 0 1 8.5 8.5z"/></svg>',
};

function renderSidebarNav(role, currentPage) {
  const sections = buildNavSections(role);
  return sections
    .map((section) => {
      const items = section.items
        .filter((item) => canAccessPage(role, item.id))
        .map((item) => {
          const active = item.id === currentPage ? ' aria-current="page"' : "";
          const featured = item.featured ? " app-nav__link--featured" : "";
          const icon = NAV_ICONS[item.id] || "";
          return `<li><a class="app-nav__link${featured}" href="${item.href}"${active}>
            <span class="app-nav__icon" aria-hidden="true">${icon}</span>
            <span class="app-nav__label">${item.label}</span>
          </a></li>`;
        })
        .join("");
      if (!items) return "";
      return `<div class="app-nav__section">
        <p class="app-nav__section-title">${section.title}</p>
        <ul class="app-nav__list">${items}</ul>
      </div>`;
    })
    .join("");
}

function renderAccessDenied(me, pageId) {
  const main = portalQs("main.app-main");
  if (!main) return;
  main.innerHTML = `
    <article class="portal-card clinic-card clinic-card--denied">
      <div class="portal-card__body clinic-card__body">
        <span class="portal-card__badge">Acceso restringido</span>
        <h1 class="clinic-header__title">No tiene permiso para esta sección</h1>
        <p class="clinic-header__sub">
          La sección <strong>${pageId}</strong> no está disponible para su perfil
          (${ROLE_LABELS[me.role] || me.role}). Si necesita acceso, contacte con administración.
        </p>
        <a class="clinic-btn clinic-btn--primary" href="/landing.html">Volver a mi panel</a>
      </div>
    </article>`;
}

function injectSiteHeader(me, pageTitle) {
  if (portalQs(".site-header--app")) return;
  const header = document.createElement("header");
  header.className = "site-header site-header--app";
  header.innerHTML = `
    <div class="site-header__inner">
      <a href="/landing.html" class="site-logo" aria-label="laSalle Health Center">
        <span class="site-logo__mark" aria-hidden="true">
          <svg viewBox="0 0 32 32" fill="none" width="28" height="28">
            <rect x="4" y="4" width="24" height="24" rx="5" stroke="currentColor" stroke-width="1.2" fill="none"/>
            <path d="M16 9v14M9 16h14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </span>
        <span class="site-logo__text">
          <span class="site-logo__title">laSalle Health Center</span>
          <span class="site-logo__subtitle">${pageTitle || "Portal clínico"}</span>
        </span>
      </a>
      <div class="app-header__user">
        <span class="app-header__role">${ROLE_LABELS_SHORT[me.role] || me.role}</span>
        <button type="button" class="clinic-btn clinic-btn--ghost clinic-btn--sm" id="btnLogout">Cerrar sesión</button>
      </div>
    </div>`;
  document.body.insertBefore(header, document.body.firstChild);
}

function injectTrustBar() {
  if (portalQs(".trust-bar")) return;
  const bar = document.createElement("div");
  bar.className = "trust-bar";
  bar.setAttribute("role", "region");
  bar.setAttribute("aria-label", "Información de seguridad");
  bar.innerHTML = `
    <div class="trust-bar__inner">
      <span class="trust-bar__item">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/></svg>
        Sesión cifrada · RGPD
      </span>
      <span class="trust-bar__item">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zM9 6c0-1.66 1.34-3 3-3s3 1.34 3 3v2H9V6z"/></svg>
        Acceso restringido al personal autorizado
      </span>
    </div>`;
  const header = portalQs(".site-header--app");
  if (header && header.nextSibling) {
    header.parentNode.insertBefore(bar, header.nextSibling);
  } else {
    document.body.insertBefore(bar, document.body.firstChild);
  }
}

function mountAppShell(me, currentPage) {
  let main = portalQs("main.app-main, main.dash, main.portal-page");
  if (!main) return;
  main.classList.remove("dash", "portal-page");
  main.classList.add("app-main");

  if (portalQs(".app-shell")) return;

  const shell = document.createElement("div");
  shell.className = "app-shell";
  const sidebar = document.createElement("aside");
  sidebar.className = "app-sidebar portal-card";
  sidebar.setAttribute("aria-label", "Menú del portal");
  const display = deriveDisplayName(me);
  sidebar.innerHTML = `
    <div class="app-sidebar__user">
      <div class="app-sidebar__avatar" aria-hidden="true">${deriveInitials(display)}</div>
      <div class="app-sidebar__meta">
        <p class="app-sidebar__name">${display}</p>
        <p class="app-sidebar__id">${roleIdChip(me)}</p>
      </div>
    </div>
    <nav class="app-nav" aria-label="Secciones">${renderSidebarNav(me.role, currentPage)}</nav>`;

  const content = document.createElement("div");
  content.className = "app-content";

  const parent = main.parentNode;
  parent.insertBefore(shell, main);
  shell.appendChild(sidebar);
  shell.appendChild(content);
  content.appendChild(main);
}

function injectAppFooter() {
  if (portalQs(".site-footer--app")) return;
  const footer = document.createElement("footer");
  footer.className = "site-footer site-footer--rich site-footer--app";
  footer.setAttribute("role", "contentinfo");
  footer.innerHTML = `
    <div class="site-footer__shell site-footer__shell--simple">
      <div class="site-footer__simple-top site-footer__simple-top--only-contact">
        <p class="site-footer__simple-contact">
          <a href="tel:+34932202000">+34 932 20 20 00</a>
          <span class="site-footer__sep" aria-hidden="true">·</span>
          <a href="mailto:contacto@lasallesanidad.com">contacto@lasallesanidad.com</a>
        </p>
      </div>
      <div class="site-footer__meta site-footer__meta--rich">
        <p>© 2026 laSalle Health Center · Proyecto académico; sin valor clínico real.</p>
      </div>
    </div>`;
  document.body.appendChild(footer);
}

function wireLogout() {
  const btn = portalQs("#btnLogout");
  if (!btn || btn.dataset.wired) return;
  btn.dataset.wired = "1";
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

/**
 * Inicializa chrome del portal. Devuelve { me } o null.
 * body[data-portal-page] — id de página actual
 * body[data-portal-title] — subtítulo en cabecera (opcional)
 */
async function initPortalApp() {
  const body = document.body;
  const pageId = body.dataset.portalPage || "dashboard";
  const pageTitle = body.dataset.portalTitle || "Portal clínico";

  body.classList.add("app-body");
  body.classList.remove("dash-body");

  const me = await requireAuth();
  if (!me) return null;

  if (!canAccessPage(me.role, pageId)) {
    injectSiteHeader(me, pageTitle);
    injectTrustBar();
    mountAppShell(me, pageId);
    injectAppFooter();
    wireLogout();
    renderAccessDenied(me, pageId);
    return { me, denied: true };
  }

  injectSiteHeader(me, pageTitle);
  injectTrustBar();
  mountAppShell(me, pageId);
  injectAppFooter();
  wireLogout();

  document.dispatchEvent(new CustomEvent("portal:ready", { detail: { me, pageId } }));
  return { me, denied: false };
}

async function loadProfileDetail(me) {
  if (me.role === "paciente") {
    try {
      return await apiJson("/patients/me");
    } catch {
      return null;
    }
  }
  if (me.role === "medico") {
    try {
      return await apiJson("/medicos/me");
    } catch {
      return null;
    }
  }
  return null;
}
