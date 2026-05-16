function fieldCard(label, value) {
  return `<article class="portal-field clinic-field">
    <p class="portal-field__label">${label}</p>
    <p class="portal-field__value">${value ?? "—"}</p>
  </article>`;
}

function renderFields(me, detail) {
  const rows = [
    fieldCard("Correo electrónico", me.email),
    fieldCard("Rol en el portal", ROLE_LABELS[me.role] || me.role),
    fieldCard("Identificador de cuenta", me.user_id),
  ];
  if (me.role === "paciente") {
    rows.push(fieldCard("ID paciente", me.patient_id || "Sin asignar"));
    if (detail) {
      rows.push(
        fieldCard("Nombre completo", detail.full_name),
        fieldCard("Teléfono", detail.phone),
        fieldCard("Sexo", detail.sex),
        fieldCard("Edad", detail.age != null ? String(detail.age) : "—"),
        fieldCard("Fecha de nacimiento", formatDate(detail.date_of_birth)),
        fieldCard("Alta hospitalaria", formatDateTime(detail.created_at))
      );
    }
  } else if (me.role === "medico") {
    rows.push(fieldCard("ID médico", me.medico_id || "Sin asignar"));
    if (detail) {
      rows.push(
        fieldCard("Nombre completo", detail.full_name),
        fieldCard("Teléfono", detail.phone),
        fieldCard("Sexo", detail.sex),
        fieldCard("Fecha de nacimiento", formatDate(detail.date_of_birth)),
        fieldCard("Alta en el centro", formatDateTime(detail.created_at))
      );
    }
  } else {
    rows.push(
      fieldCard("Ámbito", "Administración del centro"),
      fieldCard("Permisos", "Gestión de usuarios, CSV e informes")
    );
  }
  return rows.join("");
}

(async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;
  const { me } = ctx;
  const detail = await loadProfileDetail(me);
  const display = deriveDisplayName(me, detail);

  portalQs("#profileTitle").textContent = display;
  portalQs("#profileSub").textContent = `Datos de acceso y ficha ${me.role === "paciente" ? "del paciente" : me.role === "medico" ? "profesional" : "administrativa"}.`;
  portalQs("#profileInitials").textContent = deriveInitials(display);
  portalQs("#profileRoleChip").textContent = ROLE_LABELS[me.role] || me.role;
  portalQs("#profileIdChip").textContent = roleIdChip(me);

  try {
    portalQs("#profileFields").innerHTML = renderFields(me, detail);
    setPageStatus("Ficha actualizada.", "ok");
  } catch (e) {
    portalQs("#profileFields").innerHTML = renderFields(me, null);
    setPageStatus(String(e.message || e), "error");
  }
})();
