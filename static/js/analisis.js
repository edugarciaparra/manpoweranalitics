// Pantalla de análisis: gráfico ECharts y panel del asistente.
(function () {
  // ---------- Formatos ----------
  // Las opciones llegan en JSON desde Python; los textos "fmt:..." se cambian por funciones.
  const nf = new Intl.NumberFormat("es-UY", { maximumFractionDigits: 1 });
  const formatos = {
    "fmt:pesos": (v) => (v == null ? "–" : "$ " + Math.round(v).toLocaleString("es-UY")),
    "fmt:pesos_k": (v) => "$ " + Math.round(v / 1000).toLocaleString("es-UY") + "k",
    "fmt:pct": (v) => (v == null ? "–" : nf.format(v) + "%"),
    "fmt:num": (v) => (v == null ? "–" : nf.format(v)),
    "fmt:abs": (v) => (v == null ? "–" : nf.format(Math.abs(v))),
  };

  function aplicarFormatos(obj) {
    if (Array.isArray(obj)) return obj.map(aplicarFormatos);
    if (obj && typeof obj === "object") {
      for (const k of Object.keys(obj)) obj[k] = aplicarFormatos(obj[k]);
      return obj;
    }
    return typeof obj === "string" && formatos[obj] ? formatos[obj] : obj;
  }

  // ---------- Gráfico ----------
  const contenedor = document.getElementById("grafico");
  if (typeof echarts === "undefined") {
    contenedor.innerHTML =
      '<p class="vacio">No se pudo cargar el gráfico. Revisá la conexión a internet y recargá la página.</p>';
  } else {
    const opcion = aplicarFormatos(JSON.parse(document.getElementById("opcion-grafico").textContent));
    const grafico = echarts.init(contenedor, null, { renderer: "canvas" });
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) opcion.animation = false;
    grafico.setOption(opcion);

    new ResizeObserver(() => grafico.resize()).observe(contenedor);

    document.getElementById("descargar").addEventListener("click", () => {
      const a = document.createElement("a");
      a.href = grafico.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#fff" });
      a.download = (document.title.split("·")[0].trim() || "grafico") + ".png";
      a.click();
    });
  }

  // ---------- Asistente ----------
  const form = document.getElementById("form-pregunta");
  const texto = document.getElementById("pregunta");
  const conversacion = document.getElementById("conversacion");
  const boton = form.querySelector("button[type=submit]");
  const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;

  function agregar(clase, contenido) {
    const div = document.createElement("div");
    div.className = "msg " + clase;
    div.textContent = contenido;
    conversacion.appendChild(div);
    div.scrollIntoView({ block: "nearest" });
    return div;
  }

  async function preguntar(pregunta) {
    agregar("msg-yo", pregunta);
    const espera = agregar("msg-ia msg-cargando", "Analizando…");
    boton.disabled = true;
    try {
      const r = await fetch(form.dataset.url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({
          modulo: form.dataset.modulo,
          analisis: form.dataset.analisis,
          periodo: form.dataset.periodo,
          pregunta,
        }),
      });
      const datos = await r.json();
      espera.remove();
      if (!r.ok) agregar("msg-error", datos.error || "El asistente no respondió. Probá de nuevo.");
      else agregar("msg-ia", datos.respuesta);
    } catch (e) {
      espera.remove();
      agregar("msg-error", "No hay conexión con el servidor. Revisá que esté corriendo y probá de nuevo.");
    } finally {
      boton.disabled = false;
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const p = texto.value.trim();
    if (!p) return;
    texto.value = "";
    preguntar(p);
  });
  texto.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });
  document.querySelectorAll(".sugerencia").forEach((b) =>
    b.addEventListener("click", () => preguntar(b.dataset.pregunta))
  );
})();
