const ROLE_BADGE = {
  paciente: "role-badge role-badge--patient",
  medico: "role-badge role-badge--medico",
  admin: "role-badge role-badge--admin",
};

let allUsers = [];

function clinicalId(u) {
  if (u.patient_id) return u.patient_id;
  if (u.medico_id) return u.medico_id;
  return "—";
}

function renderUserRow(u) {
  const role = (u.role || "").toLowerCase();
  const badge = ROLE_BADGE[role] || "role-badge";
  const label = ROLE_LABELS[role] || role;
  return `<tr>
    <td><span class="data-table__email">${u.email || "—"}</span></td>
    <td>${u.display_name || "—"}</td>
    <td><span class="${badge}">${label}</span></td>
    <td><code>${clinicalId(u)}</code></td>
    <td>${formatDate(u.created_at)}</td>
    <td>${u.last_login_at ? formatDateTime(u.last_login_at) : '<span class="text-faint">Sin acceso</span>'}</td>
  </tr>`;
}

function renderStats(users) {
  const el = portalQs("#usersStats");
  if (!el) return;
  const total = users.length;
  const byRole = { paciente: 0, medico: 0, admin: 0 };
  users.forEach((u) => {
    const r = (u.role || "").toLowerCase();
    if (byRole[r] != null) byRole[r] += 1;
  });
  el.innerHTML = `
    <article class="clinic-stat clinic-stat--accent">
      <p class="clinic-stat__label">Total cuentas</p>
      <p class="clinic-stat__value">${total}</p>
      <p class="clinic-stat__hint">Registradas en el sistema</p>
    </article>
    <article class="clinic-stat">
      <p class="clinic-stat__label">Pacientes</p>
      <p class="clinic-stat__value">${byRole.paciente}</p>
    </article>
    <article class="clinic-stat">
      <p class="clinic-stat__label">Médicos</p>
      <p class="clinic-stat__value">${byRole.medico}</p>
    </article>
    <article class="clinic-stat">
      <p class="clinic-stat__label">Administración</p>
      <p class="clinic-stat__value">${byRole.admin}</p>
    </article>`;
}

function applyFilter(query) {
  const q = (query || "").trim().toLowerCase();
  const filtered = !q
    ? allUsers
    : allUsers.filter((u) => {
        const hay = [u.email, u.display_name, u.role, u.patient_id, u.medico_id]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return hay.includes(q);
      });
  const body = portalQs("#usersBody");
  body.innerHTML = filtered.length
    ? filtered.map(renderUserRow).join("")
    : `<tr><td colspan="6" class="data-table__empty">No hay usuarios que coincidan con la búsqueda.</td></tr>`;
  portalQs("#usersCount").textContent = `${filtered.length} de ${allUsers.length} cuenta(s) mostrada(s).`;
}

(async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;

  portalQs("#usersSub").textContent =
    ctx.me.role === "admin"
      ? "Vista global · todas las cuentas del hospital"
      : "Listado de cuentas del portal (solo lectura)";

  try {
    allUsers = await apiJsonList("/users");
    renderStats(allUsers);
    applyFilter("");
    portalQs("#usersSearch")?.addEventListener("input", (e) => applyFilter(e.target.value));
    setPageStatus(`${allUsers.length} usuario(s) cargados desde la base de datos.`, "ok");
  } catch (e) {
    portalQs("#usersBody").innerHTML =
      `<tr><td colspan="6" class="data-table__empty">No se pudo cargar el directorio de usuarios.</td></tr>`;
    setPageStatus(String(e.message || e), "error");
  }
})();
