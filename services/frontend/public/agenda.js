function todayLabel() {
  return new Intl.DateTimeFormat("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date());
}

function buildDemoAgenda(role) {
  if (role === "medico" || role === "admin") {
    return [
      { time: "09:00", title: "Consulta · María López", meta: "Consulta externa · Sala 2", status: "confirmada" },
      { time: "10:30", title: "Revisión RX · Juan Pérez", meta: "Radiología · Planta 1", status: "pendiente" },
      { time: "12:00", title: "Comité clínico", meta: "Sala B · Hospitalización", status: "interna" },
      { time: "16:15", title: "Consulta · Ana Ruiz", meta: "Primera visita", status: "confirmada" },
    ];
  }
  return [
    { time: "11:00", title: "Consulta de seguimiento", meta: "Dr. García · Consulta 4", status: "confirmada" },
    { time: "17:30", title: "Analítica", meta: "Laboratorio · Planta baja", status: "recordatorio" },
  ];
}

function renderAgendaItem(item) {
  const statusClass =
    item.status === "confirmada"
      ? "agenda-item__badge--ok"
      : item.status === "pendiente"
        ? "agenda-item__badge--warn"
        : "agenda-item__badge--muted";
  return `<li class="agenda-item">
    <span class="agenda-item__time">${item.time}</span>
    <div class="agenda-item__body">
      <p class="agenda-item__title">${item.title}</p>
      <p class="agenda-item__meta">${item.meta}</p>
    </div>
    <span class="agenda-item__badge ${statusClass}">${item.status}</span>
  </li>`;
}

(async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;
  const { me } = ctx;
  const role = me.role;

  const title = portalQs("#agendaTitle");
  const sub = portalQs("#agendaSub");
  const listTitle = portalQs("#agendaListTitle");
  const listSub = portalQs("#agendaListSub");

  title.textContent = agendaLabel(role);
  sub.textContent = `${todayLabel()} · ${me.email}`;
  listTitle.textContent =
    role === "paciente" ? "Sus citas programadas" : role === "admin" ? "Actividad del centro" : "Agenda clínica de hoy";
  listSub.textContent =
    "Horarios de demostración (proyecto académico). En producción se sincronizarían con el sistema de citas del hospital.";

  const items = buildDemoAgenda(role);
  portalQs("#agendaList").innerHTML = items.map(renderAgendaItem).join("");
  setPageStatus(`${items.length} evento(s) en la agenda.`, "ok");
})();
