function todayLabel() {
  return new Intl.DateTimeFormat("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date());
}

function buildDemoAgenda(me) {
  const isMedico = me.role === "medico" || me.role === "admin";
  if (isMedico) {
    return [
      { time: "09:00", title: "Consulta · María López", meta: "Consulta externa · Sala 2", status: "confirmada" },
      { time: "10:30", title: "Revisión RX · Juan Pérez", meta: "Seguimiento radiológico", status: "pendiente" },
      { time: "12:00", title: "Comité clínico", meta: "Sala de reuniones B", status: "interna" },
      { time: "16:15", title: "Consulta · Ana Ruiz", meta: "Primera visita", status: "confirmada" },
    ];
  }
  return [
    { time: "11:00", title: "Consulta de seguimiento", meta: "Dr. García · Consulta 4", status: "confirmada" },
    { time: "17:30", title: "Analítica programada", meta: "Laboratorio · Planta baja", status: "recordatorio" },
  ];
}

function renderAgendaItem(item) {
  const statusClass =
    item.status === "confirmada"
      ? "agenda-item__badge--ok"
      : item.status === "pendiente"
        ? "agenda-item__badge--warn"
        : "agenda-item__badge--muted";
  return `
    <li class="agenda-item">
      <span class="agenda-item__time">${item.time}</span>
      <div class="agenda-item__body">
        <p class="agenda-item__title">${item.title}</p>
        <p class="agenda-item__meta">${item.meta}</p>
      </div>
      <span class="agenda-item__badge ${statusClass}">${item.status}</span>
    </li>
  `;
}

async function boot() {
  wireLogout();
  const me = await requireAuth();
  if (!me) return;

  const isMedico = me.role === "medico";
  const isAdmin = me.role === "admin";
  const title = portalQs("#agendaTitle");
  const sub = portalQs("#agendaSub");
  const subtitle = portalQs("#agendaSubtitle");
  const listTitle = portalQs("#agendaListTitle");
  const listSub = portalQs("#agendaListSub");
  const list = portalQs("#agendaList");

  if (isMedico) {
    if (title) title.textContent = "Agenda del día";
    if (subtitle) subtitle.textContent = "Agenda clínica";
    if (listTitle) listTitle.textContent = "Consultas y actividades de hoy";
    if (listSub) {
      listSub.textContent =
        "Vista orientativa para personal clínico. Los horarios son de demostración (proyecto académico).";
    }
  } else if (isAdmin) {
    if (title) title.textContent = "Calendario operativo";
    if (subtitle) subtitle.textContent = "Operaciones";
    if (listTitle) listTitle.textContent = "Actividad del centro hoy";
    if (listSub) listSub.textContent = "Resumen operativo de demostración.";
  } else {
    if (title) title.textContent = "Mis citas";
    if (subtitle) subtitle.textContent = "Mis citas";
    if (listTitle) listTitle.textContent = "Próximas citas";
    if (listSub) listSub.textContent = "Recordatorios de su agenda personal (datos de ejemplo).";
  }

  if (sub) sub.textContent = `${todayLabel()} · ${me.email}`;

  const items = buildDemoAgenda(me);
  if (list) {
    list.innerHTML = items.map(renderAgendaItem).join("");
  }
  setPageStatus(`${items.length} evento(s) en la agenda de hoy.`, "ok");
}

boot();
