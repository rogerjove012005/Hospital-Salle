let sparkChart = null;
let rxChart = null;

function kpiCard(label, value, hint) {
  return `<article class="clinic-stat">
    <p class="clinic-stat__label">${label}</p>
    <p class="clinic-stat__value">${value}</p>
    <p class="clinic-stat__hint">${hint}</p>
  </article>`;
}

function renderKpis(summary, role) {
  const el = portalQs("#analyticsKpis");
  if (!el) return;
  const rows = [
    kpiCard("Pipeline", summary.pipeline_status || "—", "Estado global"),
    kpiCard("Alertas", String(summary.open_alerts ?? 0), "Incidencias abiertas"),
  ];
  if (role === "paciente") {
    rows.push(kpiCard("Mis estudios", String(summary.studies_count ?? "—"), "Expediente clínico"));
  } else {
    rows.push(
      kpiCard("Pacientes", String(summary.patients_count ?? "—"), "Directorio"),
      kpiCard("Estudios", String(summary.studies_count ?? "—"), "Registros"),
      kpiCard("Lotes CSV", String(summary.csv_import_batches ?? "—"), "Importaciones"),
      kpiCard(
        "Filas Spark",
        summary.spark_total_rows != null ? String(summary.spark_total_rows) : "—",
        "Agregado analítico"
      )
    );
    if (summary.radiology_available && summary.radiology_accuracy != null) {
      rows.push(
        kpiCard(
          "IA RX (test)",
          `${(summary.radiology_accuracy * 100).toFixed(1)}%`,
          "Accuracy en prueba"
        )
      );
    }
  }
  el.innerHTML = rows.join("");
}

function renderAlerts(alerts) {
  const list = portalQs("#alertsList");
  if (!list) return;
  if (!alerts.length) {
    list.innerHTML = '<li class="alerts-item alerts-item--ok">Sin alertas críticas recientes. Sistema estable.</li>';
    return;
  }
  list.innerHTML = alerts
    .map((a) => {
      const cls =
        a.severity === "critical"
          ? "alerts-item--critical"
          : a.severity === "warning"
            ? "alerts-item--warn"
            : "";
      const when = a.created_at ? formatDateTime(a.created_at) : "";
      return `<li class="alerts-item ${cls}">
        <p class="alerts-item__title">${a.stage} · ${a.status}</p>
        <p class="alerts-item__msg">${a.message}</p>
        <p class="alerts-item__meta">${when}</p>
      </li>`;
    })
    .join("");
}

function destroyChart(chart) {
  if (chart) chart.destroy();
  return null;
}

async function renderSparkChart() {
  const canvas = portalQs("#chartSpark");
  if (!canvas || typeof Chart === "undefined") return;
  try {
    const data = await apiJson("/stats/csv-aggregates?top=8");
    const labels = data.top_batches.map((b) => b.batch_id.slice(0, 8));
    const values = data.top_batches.map((b) => b.row_count);
    sparkChart = destroyChart(sparkChart);
    sparkChart = new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Filas",
            data: values,
            backgroundColor: "rgba(15, 118, 110, 0.75)",
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } },
      },
    });
  } catch {
    sparkChart = destroyChart(sparkChart);
  }
}

async function renderRxChart() {
  const canvas = portalQs("#chartRxF1");
  if (!canvas || typeof Chart === "undefined") return;
  try {
    const m = await apiJson("/radiology/metrics");
    if (!m.available || !m.per_class_metrics) return;
    const labels = Object.keys(m.per_class_metrics);
    const values = labels.map((k) => m.per_class_metrics[k]["f1-score"] ?? 0);
    rxChart = destroyChart(rxChart);
    rxChart = new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "F1",
            data: values,
            backgroundColor: ["#10b981", "#f59e0b", "#ef4444"],
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { min: 0, max: 1 } },
      },
    });
  } catch {
    rxChart = destroyChart(rxChart);
  }
}

async function loadDashboard() {
  const summary = await apiJson("/dashboard/summary");
  const role = summary.role;
  portalQs("#analyticsSub").textContent =
    role === "paciente"
      ? "Resumen de su actividad en el portal."
      : "Monitorización de ingesta, Spark, radiología y calidad.";
  renderKpis(summary, role);

  const charts = portalQs("#chartsClinical");
  if (role === "admin" || role === "medico") {
    if (charts) charts.hidden = false;
    await Promise.all([renderSparkChart(), renderRxChart()]);
    const alerts = await apiJson("/alerts?limit=25");
    renderAlerts(alerts);
  } else {
    if (charts) charts.hidden = true;
    renderAlerts([]);
  }
  setPageStatus("Centro de control actualizado.", "ok");
}

(async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;

  const reportBtn = portalQs("#btnOpenReport");
  if (reportBtn) {
    if (ctx.me.role === "paciente") {
      reportBtn.hidden = true;
    } else {
      reportBtn.addEventListener("click", async () => {
        try {
          const token = getToken();
          const res = await fetch(`${PORTAL_API_BASE}/reports/hospital`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const html = await res.text();
          const blob = new Blob([html], { type: "text/html;charset=utf-8" });
          window.open(URL.createObjectURL(blob), "_blank", "noopener");
          setPageStatus("Informe generado.", "ok");
        } catch (e) {
          setPageStatus(String(e.message || e), "error");
        }
      });
    }
  }

  portalQs("#btnRefreshAnalytics")?.addEventListener("click", () => {
    void loadDashboard().catch((e) => setPageStatus(String(e.message || e), "error"));
  });

  try {
    await loadDashboard();
  } catch (e) {
    setPageStatus(String(e.message || e), "error");
  }
})();
