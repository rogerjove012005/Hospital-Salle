function qs(s) {
  return document.querySelector(s);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setStatus(msg, kind = "neutral") {
  const el = qs("#status");
  if (!el) return;
  el.textContent = msg || "";
  el.classList.remove("ok", "error");
  if (kind === "ok") el.classList.add("ok");
  if (kind === "error") el.classList.add("error");
}

function setFormStatus(id, msg, ok) {
  const el = qs(id);
  if (!el) return;
  el.textContent = msg || "";
  el.classList.remove("ok", "error");
  if (ok === true) el.classList.add("ok");
  if (ok === false) el.classList.add("error");
}

function switchDirectoryTab(tab) {
  const isPatient = tab === "patient";
  document.querySelectorAll(".directory-tab").forEach((btn) => {
    const active = btn.getAttribute("data-directory-tab") === tab;
    btn.classList.toggle("directory-tab--active", active);
    btn.setAttribute("aria-selected", active ? "true" : "false");
  });
  const panelPatient = qs("#panelPatient");
  const panelMedico = qs("#panelMedico");
  if (panelPatient) {
    panelPatient.hidden = !isPatient;
    panelPatient.classList.toggle("directory-panel--active", isPatient);
  }
  if (panelMedico) {
    panelMedico.hidden = isPatient;
    panelMedico.classList.toggle("directory-panel--active", !isPatient);
  }
}

async function loadPatients() {
  const tbody = qs("#patientsTbody");
  const empty = qs("#patientsEmpty");
  const countEl = qs("#patientsCount");
  if (!tbody) return;
  const rows = await apiJsonList("/patients");
  tbody.innerHTML = "";
  if (countEl) countEl.textContent = `${rows.length} paciente${rows.length === 1 ? "" : "s"}`;
  if (!rows.length) {
    if (empty) empty.hidden = false;
    return;
  }
  if (empty) empty.hidden = true;
  for (const p of rows.slice(0, 30)) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><code>${escapeHtml(p.patient_id)}</code></td>
      <td>${escapeHtml(p.full_name || "—")}</td>
      <td>${escapeHtml(String(p.age ?? "—"))}</td>
      <td>${escapeHtml(p.department || "—")}</td>
      <td>${escapeHtml(p.primary_diagnosis || "—")}</td>`;
    tbody.appendChild(tr);
  }
}

async function submitPatient(e) {
  e.preventDefault();
  const body = {
    full_name: qs("#patName").value.trim(),
    age: Number(qs("#patAge").value),
    sex: qs("#patSex").value,
    phone: qs("#patPhone").value.trim() || null,
    department: qs("#patDept").value.trim() || null,
    primary_diagnosis: qs("#patDiag").value.trim() || null,
    create_portal_user: qs("#patPortal").checked,
    email: qs("#patEmail").value.trim() || null,
    password: qs("#patPass").value || null,
  };
  setFormStatus("#patStatus", "Guardando…");
  try {
    const res = await apiJson("/clinic/patients", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setFormStatus("#patStatus", res.message || "Paciente creado.", true);
    setStatus(res.message || "Paciente registrado.", "ok");
    e.target.reset();
    qs("#patPortalFields").hidden = true;
    await loadPatients();
    qs("#directoryTop")?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  } catch (err) {
    setFormStatus("#patStatus", String(err.message || err), false);
    setStatus(String(err.message || err), "error");
  }
}

async function submitMedico(e) {
  e.preventDefault();
  const sex = qs("#medSex").value;
  const body = {
    full_name: qs("#medName").value.trim(),
    sex: sex || null,
    phone: qs("#medPhone").value.trim() || null,
    email: qs("#medEmail").value.trim(),
    password: qs("#medPass").value,
  };
  setFormStatus("#medStatus", "Guardando…");
  try {
    const res = await apiJson("/clinic/medicos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setFormStatus("#medStatus", res.message || "Médico creado.", true);
    setStatus(res.message || "Médico registrado.", "ok");
    e.target.reset();
  } catch (err) {
    setFormStatus("#medStatus", String(err.message || err), false);
    setStatus(String(err.message || err), "error");
  }
}

async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;
  const me = ctx.me;
  qs("#directorySub").textContent = `Sesión: ${me.email} · ${ROLE_LABELS[me.role] || me.role}`;

  document.querySelectorAll("[data-directory-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchDirectoryTab(btn.getAttribute("data-directory-tab"));
    });
  });

  qs("#patPortal")?.addEventListener("change", () => {
    qs("#patPortalFields").hidden = !qs("#patPortal").checked;
  });

  qs("#formPatient")?.addEventListener("submit", (e) => submitPatient(e));
  qs("#formMedico")?.addEventListener("submit", (e) => submitMedico(e));
  qs("#btnRefreshPatients")?.addEventListener("click", () =>
    loadPatients().catch((e) => setStatus(String(e.message || e), "error")),
  );

  if (me.role !== "admin") {
    qs("#tabMedico")?.setAttribute("hidden", "");
    switchDirectoryTab("patient");
  }

  try {
    await loadPatients();
  } catch (e) {
    setStatus(String(e.message || e), "error");
  }
}

boot();
