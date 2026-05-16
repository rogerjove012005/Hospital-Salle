function renderPatientRow(p) {
  return `<tr>
    <td><code>${p.patient_id || "—"}</code></td>
    <td>${p.full_name || "—"}</td>
    <td>${p.age != null ? p.age : "—"}</td>
    <td>${p.sex || "—"}</td>
    <td>${p.phone || "—"}</td>
  </tr>`;
}

(async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;
  const { me } = ctx;

  const sub = portalQs("#patientsSub");
  sub.textContent =
    me.role === "admin"
      ? `Vista global del directorio · ${me.email}`
      : `Pacientes bajo su supervisión · ${me.medico_id || "sin ID médico"}`;

  try {
    const patients = await apiJson("/patients");
    const list = Array.isArray(patients) ? patients : [];
    portalQs("#patientsBody").innerHTML = list.length
      ? list.map(renderPatientRow).join("")
      : `<tr><td colspan="5">No hay pacientes registrados en el sistema.</td></tr>`;
    portalQs("#patientsCount").textContent = `${list.length} paciente(s) en el directorio hospitalario.`;
    setPageStatus("Directorio cargado correctamente.", "ok");
  } catch (e) {
    portalQs("#patientsBody").innerHTML = `<tr><td colspan="5">No se pudo cargar el directorio.</td></tr>`;
    setPageStatus(String(e.message || e), "error");
  }
})();
