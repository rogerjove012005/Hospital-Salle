const TOPIC_LABELS = {
  consulta: "Consulta general",
  cita: "Citas y agenda",
  tecnico: "Incidencia técnica del portal",
  privacidad: "Privacidad y datos (RGPD)",
};

(async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;
  const { me } = ctx;

  portalQs("#contactSub").textContent = `Sesión: ${me.email} · ${ROLE_LABELS[me.role]}`;
  portalQs("#contactName").value = deriveDisplayName(me);
  portalQs("#contactEmail").value = me.email || "";

  portalQs("#contactForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const name = portalQs("#contactName").value.trim();
    const email = portalQs("#contactEmail").value.trim();
    const topic = portalQs("#contactTopic").value;
    const message = portalQs("#contactMessage").value.trim();
    if (!name || !email || !message) {
      setPageStatus("Complete nombre, correo y mensaje.", "error");
      return;
    }
    const subject = encodeURIComponent(`[laSalle Health] ${TOPIC_LABELS[topic] || topic}`);
    const body = encodeURIComponent(`Nombre: ${name}\nCorreo: ${email}\nRol: ${me.role}\n\n${message}`);
    window.location.href = `mailto:contacto@lasallesanidad.com?subject=${subject}&body=${body}`;
    setPageStatus("Se ha abierto su cliente de correo.", "ok");
  });
})();
