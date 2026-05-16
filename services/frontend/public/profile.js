function fieldCard(label, value) {
  return `
    <article class="portal-field">
      <p class="portal-field__label">${label}</p>
      <p class="portal-field__value">${value ?? "—"}</p>
    </article>
  `;
}

function deriveInitials(name) {
  if (!name || name === "—") return "·";
  const cleaned = String(name).replace(/[^A-Za-z\u00C0-\u017F]+/g, " ").trim();
  if (!cleaned) return "·";
  const parts = cleaned.split(/\s+/).slice(0, 2);
  return parts.map((p) => p.charAt(0).toUpperCase()).join("") || cleaned.charAt(0).toUpperCase();
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

function renderFields(me, detail) {
  const rows = [
    fieldCard("Correo electrónico", me.email),
    fieldCard("Rol en el portal", ROLE_LABELS[me.role] || me.role),
    fieldCard("Identificador de usuario", me.user_id),
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
        fieldCard("Alta en el sistema", formatDateTime(detail.created_at))
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
        fieldCard("Alta en el sistema", formatDateTime(detail.created_at))
      );
    }
  } else {
    rows.push(
      fieldCard("Ámbito", "Administración del centro"),
      fieldCard("Nota", "Gestión de usuarios y operaciones del portal académico.")
    );
  }

  return rows.join("");
}

async function boot() {
  wireLogout();
  const me = await requireAuth();
  if (!me) return;

  const display = deriveDisplayName(me);
  const titleEl = portalQs("#profileTitle");
  const subEl = portalQs("#profileSub");
  const initialsEl = portalQs("#profileInitials");
  const roleChip = portalQs("#profileRoleChip");
  const idChip = portalQs("#profileIdChip");
  const fieldsEl = portalQs("#profileFields");

  if (titleEl) titleEl.textContent = display;
  if (subEl) subEl.textContent = `Sesión activa · ${me.email}`;
  if (initialsEl) initialsEl.textContent = deriveInitials(display);
  if (roleChip) roleChip.textContent = ROLE_LABELS[me.role] || me.role;

  if (idChip) {
    if (me.role === "paciente") {
      idChip.textContent = me.patient_id ? `ID paciente · ${me.patient_id}` : "Sin ID clínico";
    } else if (me.role === "medico") {
      idChip.textContent = me.medico_id ? `ID médico · ${me.medico_id}` : "Sin ID clínico";
    } else {
      idChip.textContent = "Cuenta administradora";
    }
  }

  try {
    const detail = await loadProfileDetail(me);
    if (fieldsEl) fieldsEl.innerHTML = renderFields(me, detail);
    setPageStatus("Perfil actualizado.", "ok");
  } catch (e) {
    if (fieldsEl) fieldsEl.innerHTML = renderFields(me, null);
    setPageStatus(String(e.message || e), "error");
  }
}

boot();
