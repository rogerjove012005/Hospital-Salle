const ALLOWED_ROLES = new Set(["medico", "admin"]);

function renderPatientRow(p) {
  return `
    <tr>
      <td><code>${p.patient_id || "—"}</code></td>
      <td>${p.full_name || "—"}</td>
      <td>${p.age != null ? p.age : "—"}</td>
      <td>${p.sex || "—"}</td>
      <td>${p.phone || "—"}</td>
    </tr>
  `;
}

async function boot() {
  wireLogout();
  const me = await requireAuth();
  if (!me) return;

  const content = portalQs("#patientsContent");
  const denied = portalQs("#patientsDenied");
  const sub = portalQs("#patientsSub");
  const body = portalQs("#patientsBody");
  const countEl = portalQs("#patientsCount");

  if (!ALLOWED_ROLES.has(me.role)) {
    if (content) content.hidden = true;
    if (denied) denied.hidden = false;
    if (sub) sub.textContent = `Su rol (${ROLE_LABELS[me.role] || me.role}) no tiene permiso para ver pacientes asignados.`;
    setPageStatus("Acceso denegado: solo médicos y administración.", "error");
    return;
  }

  if (denied) denied.hidden = true;
  if (content) content.hidden = false;
  if (sub) {
    sub.textContent =
      me.role === "admin"
        ? `Vista global · ${me.email}`
        : `Pacientes bajo su supervisión · ${me.medico_id || "sin ID médico"}`;
  }

  try {
    const patients = await apiJson("/patients");
    const list = Array.isArray(patients) ? patients : [];
    if (body) {
      body.innerHTML = list.length
        ? list.map(renderPatientRow).join("")
        : `<tr><td colspan="5">No hay pacientes registrados.</td></tr>`;
    }
    if (countEl) {
      countEl.textContent = `${list.length} paciente(s) en el listado.`;
    }
    setPageStatus("Listado cargado correctamente.", "ok");
  } catch (e) {
    if (body) body.innerHTML = `<tr><td colspan="5">Error al cargar pacientes.</td></tr>`;
    setPageStatus(String(e.message || e), "error");
  }
}

boot();
