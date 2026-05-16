const TOPIC_LABELS = {
  consulta: "Consulta general",
  cita: "Citas y agenda",
  tecnico: "Incidencia técnica del portal",
  privacidad: "Privacidad y datos (RGPD)",
};

async function boot() {
  wireLogout();
  const me = await requireAuth();
  if (!me) return;

  const sub = portalQs("#contactSub");
  const nameInput = portalQs("#contactName");
  const emailInput = portalQs("#contactEmail");
  const form = portalQs("#contactForm");

  if (sub) sub.textContent = `Sesión: ${me.email} · ${ROLE_LABELS[me.role] || me.role}`;
  if (nameInput) nameInput.value = deriveDisplayName(me);
  if (emailInput) emailInput.value = me.email || "";

  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const name = nameInput?.value?.trim() || "";
      const email = emailInput?.value?.trim() || "";
      const topic = portalQs("#contactTopic")?.value || "consulta";
      const message = portalQs("#contactMessage")?.value?.trim() || "";
      if (!name || !email || !message) {
        setPageStatus("Complete nombre, correo y mensaje.", "error");
        return;
      }
      const subject = encodeURIComponent(
        `[laSalle Health] ${TOPIC_LABELS[topic] || topic}`
      );
      const body = encodeURIComponent(
        `Nombre: ${name}\nCorreo: ${email}\nRol: ${me.role}\n\n${message}`
      );
      window.location.href = `mailto:contacto@lasallesanidad.com?subject=${subject}&body=${body}`;
      setPageStatus("Se ha abierto su cliente de correo.", "ok");
    });
  }
}

boot();
