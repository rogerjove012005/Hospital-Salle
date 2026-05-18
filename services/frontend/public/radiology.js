function setRxStatus(msg, kind = "neutral") {
  const el = portalQs("#status");
  if (!el) return;
  el.textContent = msg || "";
  el.classList.remove("ok", "error", "clinic-alert--ok", "clinic-alert--error");
  if (kind === "ok") el.classList.add("ok", "clinic-alert--ok");
  if (kind === "error") el.classList.add("error", "clinic-alert--error");
}

let rxF1Chart = null;
let rxPredictChart = null;
let rxConfusionObjectUrl = null;
let rxPreviewObjectUrl = null;
let rxPredictRun = 0;
/** Safari no siempre asigna ficheros al input con DataTransfer; guardamos el File aquí. */
let rxSelectedFile = null;

const RX_CLASS_LABELS = {
  SANA: "Sana",
  NEUMONIA: "Neumonía",
  "COVID-19": "COVID-19",
};

function rxLabel(name) {
  return RX_CLASS_LABELS[name] || name;
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function rxGalleryModifier(expectedClass) {
  if (expectedClass === "SANA") return "sana";
  if (expectedClass === "NEUMONIA") return "pneumonia";
  return "covid";
}

function pct(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${(100 * n).toFixed(1)} %`;
}

function setRxMatrixStatus(msg, isError = false) {
  const el = portalQs("#rxMatrixStatus");
  if (!el) return;
  if (!msg) {
    el.hidden = true;
    el.textContent = "";
    el.classList.remove("error");
    return;
  }
  el.hidden = false;
  el.textContent = msg;
  el.classList.toggle("error", isError);
}

function renderConfusionTable(cm, classNames) {
  const wrap = portalQs("#rxMatrixTableWrap");
  if (!wrap || !Array.isArray(cm) || !cm.length) return;
  const names = classNames && classNames.length ? classNames : cm.map((_, i) => `Clase ${i + 1}`);
  const head = names.map((n) => `<th>${rxLabel(n)}</th>`).join("");
  const rows = cm
    .map((row, i) => {
      const cells = row
        .map((v, j) => {
          const strong = i === j ? " rx-cm__diag" : "";
          return `<td class="${strong}">${v}</td>`;
        })
        .join("");
      return `<tr><th scope="row">${rxLabel(names[i])}</th>${cells}</tr>`;
    })
    .join("");
  wrap.innerHTML = `
    <p class="rx-matrix-table__hint">Tabla interactiva (mismos datos que el gráfico PNG).</p>
    <table class="imports-table rx-cm-table" aria-label="Matriz de confusión">
      <thead><tr><th></th>${head}</tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  wrap.hidden = false;
}

function showConfusionImage(blob) {
  const matrixWrap = portalQs("#rxMatrixWrap");
  const img = portalQs("#rxConfusionImg");
  if (!matrixWrap || !img) return;
  if (rxConfusionObjectUrl) URL.revokeObjectURL(rxConfusionObjectUrl);
  rxConfusionObjectUrl = URL.createObjectURL(blob);
  const reveal = () => {
    matrixWrap.hidden = false;
    setRxMatrixStatus("");
  };
  img.onload = reveal;
  img.onerror = () => {
    matrixWrap.hidden = true;
    setRxMatrixStatus("No se pudo mostrar el PNG; use la tabla superior.", true);
  };
  img.src = rxConfusionObjectUrl;
  if (img.complete) reveal();
}

async function loadConfusionChart(metrics) {
  const matrixWrap = portalQs("#rxMatrixWrap");
  const tableWrap = portalQs("#rxMatrixTableWrap");
  if (!metrics || !metrics.available) {
    if (matrixWrap) matrixWrap.hidden = true;
    if (tableWrap) tableWrap.hidden = true;
    setRxMatrixStatus("Modelo no disponible.", true);
    return;
  }

  if (Array.isArray(metrics.confusion_matrix) && metrics.confusion_matrix.length) {
    renderConfusionTable(metrics.confusion_matrix, metrics.class_names);
    setRxMatrixStatus("Matriz cargada (tabla + gráfico).");
  }

  if (!metrics.has_confusion_chart) {
    if (matrixWrap) matrixWrap.hidden = true;
    if (!metrics.confusion_matrix) {
      setRxMatrixStatus("Sin matriz en este entorno.", true);
    }
    return;
  }

  try {
    const token = getToken();
    const res = await fetch(`${PORTAL_API_BASE}/radiology/charts/confusion-matrix`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      if (matrixWrap) matrixWrap.hidden = true;
      if (!metrics.confusion_matrix) {
        setRxMatrixStatus(`Gráfico no disponible (HTTP ${res.status}).`, true);
      }
      return;
    }
    const blob = await res.blob();
    showConfusionImage(blob);
  } catch (e) {
    if (matrixWrap) matrixWrap.hidden = true;
    if (!metrics.confusion_matrix) {
      setRxMatrixStatus(String(e.message || e), true);
    }
  }
}

async function renderRxVisuals(metrics) {
  const f1Wrap = portalQs("#rxF1Wrap");
  const canvas = portalQs("#chartRxF1Radiology");
  if (!metrics.available) {
    if (f1Wrap) f1Wrap.hidden = true;
    await loadConfusionChart(metrics);
    return;
  }
  const chartReady = await waitForChartJs();
  if (f1Wrap && canvas && metrics.per_class_metrics && chartReady) {
    f1Wrap.hidden = false;
    const labels = Object.keys(metrics.per_class_metrics).map(rxLabel);
    const keys = Object.keys(metrics.per_class_metrics);
    const values = keys.map((k) => metrics.per_class_metrics[k]["f1-score"] ?? 0);
    if (rxF1Chart) {
      rxF1Chart.destroy();
      rxF1Chart = null;
    }
    const existing = typeof Chart.getChart === "function" ? Chart.getChart(canvas) : null;
    if (existing) existing.destroy();
    rxF1Chart = new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "F1 (test)",
            data: values,
            backgroundColor: ["#10b981", "#f59e0b", "#ef4444"],
            borderRadius: 6,
          },
        ],
      },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 1 } } },
    });
  } else if (f1Wrap) {
    f1Wrap.hidden = true;
  }
  await loadConfusionChart(metrics);
}

function explainPrediction(body, fileName) {
  const probs = body.probabilities || {};
  const pred = body.predicted_class;
  const sorted = Object.entries(probs).sort((a, b) => b[1] - a[1]);
  const top = sorted[0];
  const second = sorted[1];
  const gap =
    top && second && top[1] > 0 ? ((top[1] - second[1]) / top[1]) * 100 : 0;

  const probLines = sorted
    .map(([k, v]) => `<li><strong>${rxLabel(k)}</strong>: ${pct(v)}</li>`)
    .join("");

  return `
    <h3 class="rx-explain__title">Cómo se ha obtenido este resultado</h3>
    <p class="rx-explain__lead">
      Imagen analizada: <strong>${fileName || "radiografía"}</strong>.
      Clase asignada por el modelo: <strong class="rx-explain__pred">${rxLabel(pred)}</strong>.
    </p>
    <ol class="rx-explain__steps">
      <li><strong>Carga</strong> — Se recibe un PNG/JPEG y se valida el tamaño (máx. 8&nbsp;MB).</li>
      <li><strong>Preprocesado</strong> — Escala de grises, redimensionado a <strong>224×224</strong> píxeles y normalización [0, 1].</li>
      <li><strong>Vector de entrada</strong> — La imagen se apila en 3 canales (RGB) y se aplana para el pipeline de <em>scikit-learn</em> empaquetado en la API.</li>
      <li><strong>Modelo</strong> — <code>StandardScaler</code> → <code>PCA</code> → <code>MLPClassifier</code> (entrenado con Chest X-Ray real: NORMAL / PNEUMONIA + referencia COVID-19).</li>
      <li><strong>Decisión</strong> — Se calculan probabilidades por clase; gana la de <strong>mayor valor</strong> (argmax).</li>
    </ol>
    <p class="rx-explain__sub">Probabilidades estimadas:</p>
    <ul class="rx-explain__probs">${probLines}</ul>
  ${
    top && second
      ? `<p class="rx-explain__note">La clase ganadora (${rxLabel(top[0])}) supera a la segunda (${rxLabel(second[0])}) en aprox. <strong>${gap.toFixed(0)} %</strong> relativo sobre su propia probabilidad.</p>`
      : ""
  }
    <p class="rx-explain__disclaimer">${body.disclaimer || "Resultado orientativo; no sustituye diagnóstico médico."}</p>
  `;
}

function destroyPredictChart() {
  const canvas = portalQs("#chartRxPredict");
  if (rxPredictChart) {
    rxPredictChart.destroy();
    rxPredictChart = null;
  }
  if (canvas && typeof Chart !== "undefined" && typeof Chart.getChart === "function") {
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();
  }
  const wrap = portalQs("#rxPredictChartWrap");
  if (wrap) wrap.hidden = true;
}

function clearPredictReport() {
  const results = portalQs("#predictResults");
  const empty = portalQs("#predictEmpty");
  const explain = portalQs("#predictExplain");
  const out = portalQs("#predictOut");
  const preview = portalQs("#predictPreview");
  const meta = portalQs("#predictMeta");
  const input = portalQs("#fileRx");
  const hint = portalQs("#rxFileHint");
  const jsonDetails = portalQs("#predictResults .rx-results__json");

  destroyPredictChart();
  if (explain) explain.innerHTML = "";
  if (out) out.textContent = "";
  if (meta) {
    meta.hidden = true;
    meta.textContent = "";
  }
  if (jsonDetails) {
    jsonDetails.open = false;
    jsonDetails.removeAttribute("open");
  }
  if (results) results.hidden = true;
  if (empty) empty.hidden = false;
  if (preview) preview.removeAttribute("src");
  if (rxPreviewObjectUrl) {
    URL.revokeObjectURL(rxPreviewObjectUrl);
    rxPreviewObjectUrl = null;
  }
  if (input) input.value = "";
  if (hint) hint.textContent = "PNG o JPEG · 224×224 px";
}

function waitForChartJs(maxMs = 8000) {
  if (typeof Chart !== "undefined") return Promise.resolve(true);
  return new Promise((resolve) => {
    const t0 = Date.now();
    const tick = () => {
      if (typeof Chart !== "undefined") {
        resolve(true);
        return;
      }
      if (Date.now() - t0 >= maxMs) {
        resolve(false);
        return;
      }
      setTimeout(tick, 40);
    };
    tick();
  });
}

function setMetricsStatus(msg, isError = false) {
  const el = portalQs("#metricsStatus");
  if (!el) return;
  el.textContent = msg || "";
  el.classList.toggle("error", isError);
}

function formatMetricsSummary(metrics) {
  if (!metrics || !metrics.available) {
    return "Modelo no disponible en este entorno.";
  }
  const acc = metrics.accuracy != null ? pct(metrics.accuracy) : "—";
  const lines = [`Accuracy global: ${acc}`, "Dataset: Chest X-Ray (NORMAL / PNEUMONIA) + COVID-19"];
  if (metrics.per_class_metrics) {
    for (const [k, v] of Object.entries(metrics.per_class_metrics)) {
      const f1 = v && v["f1-score"] != null ? pct(v["f1-score"]) : "—";
      lines.push(`${rxLabel(k)} · F1: ${f1}`);
    }
  }
  return lines.join(" · ");
}

function getRxFile() {
  if (rxSelectedFile) return rxSelectedFile;
  const input = portalQs("#fileRx");
  return input?.files?.[0] || null;
}

function setRxFile(file) {
  rxSelectedFile = file || null;
  const input = portalQs("#fileRx");
  const hint = portalQs("#rxFileHint");
  if (file && hint) hint.textContent = file.name;
  if (file && input) {
    try {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
    } catch {
      /* Safari: input.files puede quedar vacío; rxSelectedFile sigue válido */
    }
  }
}

function resetRadiologyPage() {
  rxSelectedFile = null;
  const input = portalQs("#fileRx");
  if (input) input.value = "";
  clearPredictReport();
  setRxStatus("Página reiniciada. Seleccione una nueva radiografía arriba.", "ok");
  const upload = portalQs("#rxUpload");
  if (upload?.scrollIntoView) {
    upload.scrollIntoView({ behavior: "smooth", block: "start" });
  } else {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  portalQs("#fileRx")?.focus();
}

async function renderPredictChart(body) {
  const wrap = portalQs("#rxPredictChartWrap");
  const canvas = portalQs("#chartRxPredict");
  const probs = body && body.probabilities ? body.probabilities : {};
  if (!wrap || !canvas || !Object.keys(probs).length) return;

  const chartReady = await waitForChartJs();
  if (!chartReady) return;

  const labels = Object.keys(probs).map(rxLabel);
  const values = Object.keys(probs).map((k) => Number(probs[k]) || 0);
  const colors = Object.keys(probs).map((k) => {
    if (k === "SANA") return "#10b981";
    if (k === "NEUMONIA") return "#f59e0b";
    return "#ef4444";
  });

  destroyPredictChart();
  wrap.hidden = false;
  rxPredictChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Probabilidad", data: values, backgroundColor: colors, borderRadius: 6 }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { min: 0, max: 1, ticks: { callback: (v) => `${Math.round(v * 100)}%` } } },
    },
  });
}

function showPredictReport(body, file) {
  const results = portalQs("#predictResults");
  const empty = portalQs("#predictEmpty");
  const explain = portalQs("#predictExplain");
  const out = portalQs("#predictOut");
  const preview = portalQs("#predictPreview");
  const meta = portalQs("#predictMeta");
  const jsonDetails = portalQs("#predictResults .rx-results__json");
  const runId = ++rxPredictRun;

  if (!results || !explain || !out) return;
  if (empty) empty.hidden = true;

  if (preview && file) {
    if (rxPreviewObjectUrl) URL.revokeObjectURL(rxPreviewObjectUrl);
    rxPreviewObjectUrl = URL.createObjectURL(file);
    preview.src = rxPreviewObjectUrl;
  }

  if (meta) {
    meta.hidden = false;
    meta.textContent = `Análisis #${runId} · ${file ? file.name : "radiografía"} · ${new Date().toLocaleString("es-ES")}`;
  }

  explain.innerHTML = explainPrediction(body, file ? file.name : "");
  out.textContent = JSON.stringify(body, null, 2);
  if (jsonDetails) jsonDetails.open = false;

  results.hidden = false;
  void renderPredictChart(body);
}

async function loadMetrics() {
  const pre = portalQs("#metricsOut");
  const f1Wrap = portalQs("#rxF1Wrap");
  if (!pre) return;
  setMetricsStatus("Cargando métricas…");
  if (f1Wrap) f1Wrap.hidden = true;
  try {
    const body = await apiJson("/radiology/metrics");
    pre.textContent = JSON.stringify(body, null, 2);
    setMetricsStatus(formatMetricsSummary(body));
    try {
      await renderRxVisuals(body);
    } catch (chartErr) {
      console.warn("radiology charts:", chartErr);
      setMetricsStatus(`${formatMetricsSummary(body)} (gráfico no disponible).`, true);
    }
    setRxStatus("Métricas del modelo cargadas.", "ok");
  } catch (e) {
    pre.textContent = String(e.message || e);
    setMetricsStatus(`Error al cargar métricas: ${e.message || e}`, true);
    setRxStatus("No se pudieron cargar las métricas.", "error");
  }
}

async function doPredict(forcedFile) {
  const file = forcedFile || getRxFile();
  if (!file) {
    setRxStatus("Seleccione una imagen PNG o JPEG, o pulse una muestra de prueba.", "error");
    return;
  }
  const name = file.name && /\./.test(file.name) ? file.name : `${file.name || "radiografia"}.png`;
  setRxStatus("Calculando predicción…");
  const token = getToken();
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const fd = new FormData();
  fd.append("file", file, name);
  const res = await fetch(`${PORTAL_API_BASE}/radiology/predict?_=${Date.now()}`, {
    method: "POST",
    headers,
    body: fd,
    cache: "no-store",
  });
  const text = await res.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    const msg =
      typeof body === "string"
        ? body
        : body && body.detail
          ? typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail)
          : JSON.stringify(body);
    clearPredictReport();
    const results = portalQs("#predictResults");
    const empty = portalQs("#predictEmpty");
    const out = portalQs("#predictOut");
    if (results && out) {
      if (empty) empty.hidden = true;
      results.hidden = false;
      out.textContent = `Error HTTP ${res.status}: ${msg}`;
    }
    setRxStatus("Fallo en la predicción.", "error");
    return;
  }
  showPredictReport(body, file);
  const expected = portalQs(".rx-gallery__item.is-selected")?.getAttribute("data-rx-expected");
  const refHint = expected ? ` Referencia dataset: ${rxLabel(expected)}.` : "";
  setRxStatus(`Predicción completada.${refHint} Use «Radiografía nueva» para otro estudio.`, "ok");
  portalQs("#rxInfer")?.scrollIntoView?.({ behavior: "smooth", block: "start" });
}

(async function boot() {
  const ctx = await initPortalApp();
  if (!ctx || ctx.denied) return;
  const { me } = ctx;

  const sub = portalQs("#rxSub");
  if (sub) {
    sub.innerHTML =
      `Analice imágenes RX en segundos. Clases: <strong>Sana</strong>, <strong>Neumonía</strong> y <strong>COVID-19</strong>. ` +
      `Sesión: ${me.email} · ${ROLE_LABELS[me.role]}.`;
  }

  const fileInput = portalQs("#fileRx");
  const hint = portalQs("#rxFileHint");
  if (fileInput && hint) {
    fileInput.addEventListener("change", () => {
      const f = fileInput.files && fileInput.files[0];
      if (f) {
        setRxFile(f);
        clearPredictReport();
        setRxStatus(`Archivo «${f.name}» listo. Pulse «Analizar radiografía».`, "ok");
      }
    });
  }

  portalQs("#btnPredict")?.addEventListener("click", () => void doPredict());
  portalQs("#btnNewRx")?.addEventListener("click", () => resetRadiologyPage());

  async function loadRxSample(url, label, autoAnalyze = true, expectedClass = null) {
    setRxStatus(`Cargando ${label}…`);
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`No se pudo cargar ${url}`);
    const blob = await res.blob();
    const name = url.split("/").pop() || "muestra.png";
    const mime =
      blob.type ||
      (name.toLowerCase().endsWith(".jpg") || name.toLowerCase().endsWith(".jpeg")
        ? "image/jpeg"
        : "image/png");
    const file = new File([blob], name, { type: mime });
    setRxFile(file);
    clearPredictReport();
    if (autoAnalyze) {
      await doPredict(file);
    } else {
      setRxStatus(`Listo: ${name}. Pulse «Analizar radiografía».`, "ok");
    }
  }

  function wireRxSampleButtons(selector) {
    document.querySelectorAll(selector).forEach((btn) => {
      btn.addEventListener("click", (ev) => {
        ev.preventDefault();
        const url = btn.getAttribute("data-rx-sample");
        const label = btn.getAttribute("data-rx-title") || btn.textContent?.trim() || "muestra";
        const expected = btn.getAttribute("data-rx-expected");
        if (!url) return;
        document.querySelectorAll(".rx-gallery__item.is-selected").forEach((el) => el.classList.remove("is-selected"));
        if (btn.classList.contains("rx-gallery__item")) btn.classList.add("is-selected");
        loadRxSample(url, label, true, expected).catch((e) => setRxStatus(String(e.message || e), "error"));
      });
    });
  }

  async function loadRxChestGallery() {
    const gallery = portalQs("#rxChestGallery");
    if (!gallery) return;
    try {
      const res = await fetch("/samples/rx/manifest.json", { cache: "no-store" });
      if (!res.ok) throw new Error("No se encontró manifest.json");
      const data = await res.json();
      const samples = Array.isArray(data.samples) ? data.samples : [];
      if (!samples.length) {
        gallery.innerHTML = '<p class="rx-gallery__empty">Sin radiografías en el manifiesto.</p>';
        return;
      }
      gallery.innerHTML = samples
        .map((s) => {
          const mod = rxGalleryModifier(s.expected_class);
          return `<button type="button" class="rx-gallery__item rx-gallery__item--${mod}"
            data-rx-sample="${escapeHtml(s.url)}"
            data-rx-title="${escapeHtml(s.title || s.label)}"
            data-rx-expected="${escapeHtml(s.expected_class)}"
            title="${escapeHtml(s.title || s.label)}">
            <img src="${escapeHtml(s.url)}" alt="${escapeHtml(s.title || s.label)}" loading="lazy" width="96" height="96" />
            <span class="rx-gallery__cap">${escapeHtml(s.label)}</span>
          </button>`;
        })
        .join("");
      wireRxSampleButtons(".rx-gallery__item");
    } catch (e) {
      gallery.innerHTML = `<p class="rx-gallery__empty">Galería no disponible (${escapeHtml(String(e.message || e))}). Ejecuta <code>python3 scripts/sync_radiology_samples.py</code>.</p>`;
    }
  }

  wireRxSampleButtons(".rx-sample-chip");

  clearPredictReport();
  await loadRxChestGallery();
  await loadMetrics();

  window.addEventListener("pageshow", (ev) => {
    if (ev.persisted) void loadMetrics();
  });
})();
