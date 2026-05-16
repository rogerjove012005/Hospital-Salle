function renderStudy(s) {
  const label = s.label || "Sin clasificación";
  const when = formatDateTime(s.timestamp || s.created_at);
  return `<li class="records-item">
    <span class="records-item__icon" aria-hidden="true">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 9h6M7 13h10"/>
      </svg>
    </span>
    <div class="records-item__body">
      <p class="records-item__title">${label}</p>
      <p class="records-item__meta">${when} · ID ${s.study_id || "—"} · ${s.source || "hospital"}</p>
    </div>
    <span class="agenda-item__badge agenda-item__badge--ok">Registrado</span>
  </li>`;
}

(async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;
  const { me } = ctx;

  portalQs("#recordsSub").textContent = me.patient_id
    ? `Ficha ${me.patient_id} · ${me.email}`
    : `Sin ficha clínica vinculada · ${me.email}`;

  try {
    const studies = await apiJson("/studies/me");
    const list = Array.isArray(studies) ? studies : [];
    portalQs("#recordsList").innerHTML = list.length
      ? list.map(renderStudy).join("")
      : `<li class="records-item records-item--empty">No hay estudios en su expediente todavía.</li>`;
    portalQs("#recordsCount").textContent = `${list.length} estudio(s) en el expediente.`;
    setPageStatus("Expediente cargado.", "ok");
  } catch (e) {
    portalQs("#recordsList").innerHTML = `<li class="records-item records-item--empty">Error al cargar el expediente.</li>`;
    setPageStatus(String(e.message || e), "error");
  }
})();
