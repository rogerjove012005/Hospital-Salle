const qs = (s) => document.querySelector(s);

const userNameEl = qs("#userName");
const avatarInitialsEl = qs("#avatarInitials");
const dashSubEl = qs("#dashSub");
const chipRoleEl = qs("#chipRole");
const chipIdEl = qs("#chipId");
const actionsSub = qs("#actionsSub");
const actionsList = qs("#actionsList");
const loginMeta = qs("#loginMeta");

const mNextAppt = qs("#mNextAppt");
const mNextApptHint = qs("#mNextApptHint");
const mSecondaryLabel = qs("#mSecondaryLabel");
const mSecondaryValue = qs("#mSecondaryValue");
const mSecondaryHint = qs("#mSecondaryHint");
const mTertiaryLabel = qs("#mTertiaryLabel");
const mTertiaryValue = qs("#mTertiaryValue");
const mTertiaryHint = qs("#mTertiaryHint");

function renderQuickActions(role) {
  if (!actionsList) return;
  const sections = buildNavSections(role);
  const items = [];
  sections.forEach((sec) => {
    sec.items.forEach((item) => {
      if (!canAccessPage(role, item.id) || item.id === "dashboard") return;
      const icon = NAV_ICONS[item.id] || "";
      const featured = item.featured ? " action--featured" : "";
      items.push(`<li><a class="action${featured}" href="${item.href}">
        <span class="action__icon" aria-hidden="true">${icon}</span>
        <span class="action__title">${item.label}</span>
        <span class="action__chev" aria-hidden="true">›</span>
      </a></li>`);
    });
  });
  actionsList.innerHTML = items.join("");
}

function applyRoleDashboard(me, detail) {
  const role = me.role;
  const display = deriveDisplayName(me, detail);

  userNameEl.textContent = display;
  if (avatarInitialsEl) avatarInitialsEl.textContent = deriveInitials(display);
  chipRoleEl.textContent = ROLE_LABELS[role] || role;
  chipRoleEl.classList.add("chip--brand");
  chipIdEl.textContent = roleIdChip(me);

  dashSubEl.textContent = me.email ? `${me.email} · ${ROLE_LABELS[role]}` : "Sesión activa";

  const rxSpotlight = qs("#rxSpotlight");
  if (rxSpotlight) rxSpotlight.hidden = !(role === "medico" || role === "admin");

  if (role === "paciente") {
    actionsSub.textContent = "Portal del paciente — consulte citas, expediente y contacto.";
    mSecondaryLabel.textContent = "Última visita";
    mSecondaryHint.textContent = "Historial clínico de demostración.";
    mTertiaryLabel.textContent = "Estudios en expediente";
    mTertiaryHint.textContent = "Pruebas diagnósticas registradas.";
    mNextAppt.textContent = "11:00";
    mNextApptHint.textContent = "Consulta de seguimiento · hoy";
    return;
  }

  if (role === "medico") {
    actionsSub.textContent = "Portal clínico — agenda, pacientes y herramientas de apoyo.";
    mSecondaryLabel.textContent = "Consultas hoy";
    mSecondaryValue.textContent = "4";
    mSecondaryHint.textContent = "Vista orientativa (demo).";
    mTertiaryLabel.textContent = "Pacientes en cartera";
    mTertiaryHint.textContent = "Listado desde el hospital.";
    mNextAppt.textContent = "09:00";
    mNextApptHint.textContent = "Primera consulta del día";
    return;
  }

  actionsSub.textContent = "Portal de administración — operaciones y directorio.";
  mSecondaryLabel.textContent = "Operaciones activas";
  mSecondaryValue.textContent = "CSV + RX";
  mSecondaryHint.textContent = "Servicios hospitalarios conectados.";
  mTertiaryLabel.textContent = "Directorio";
  mTertiaryHint.textContent = "Pacientes y personal.";
  mNextAppt.textContent = "—";
  mNextApptHint.textContent = "Sin agenda personal";
}

async function loadDashboardMetrics(me) {
  try {
    if (me.role === "paciente") {
      const studies = await apiJson("/studies/me");
      const count = Array.isArray(studies) ? studies.length : 0;
      if (mTertiaryValue) mTertiaryValue.textContent = String(count);
      if (mSecondaryValue) mSecondaryValue.textContent = count ? "Registrada" : "—";
      return;
    }
    if (me.role === "medico" || me.role === "admin") {
      const patients = await apiJson("/patients");
      const count = Array.isArray(patients) ? patients.length : 0;
      if (mTertiaryValue) mTertiaryValue.textContent = String(count);
    }
  } catch {
    if (mTertiaryValue) mTertiaryValue.textContent = "—";
  }
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
  if (loginMeta) loginMeta.textContent = `Acceso correcto · ${fmt.format(now)}`;
}

(async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;
  const { me } = ctx;

  const detail = await loadProfileDetail(me);
  applyRoleDashboard(me, detail);
  renderQuickActions(me.role);
  setLoginMeta();
  await loadDashboardMetrics(me);
  setPageStatus("");
})();
