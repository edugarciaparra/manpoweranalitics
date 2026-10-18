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

  // ---------- Gráficos ----------
  // Cada sección puede tener su gráfico; las opciones llegan juntas en una lista.
  const opciones = JSON.parse(document.getElementById("opciones-graficos").textContent);
  const contenedores = document.querySelectorAll(".grafico[data-indice]");
  const graficos = {};
  const sinAnimacion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (typeof echarts === "undefined") {
    contenedores.forEach((c) => {
      c.innerHTML = '<p class="vacio">No se pudo cargar el gráfico. Revisá la conexión a internet y recargá la página.</p>';
    });
  } else {
    // Se dibuja cada gráfico cuando entra en pantalla, así la página carga rápido
    const dibujar = (c) => {
      if (graficos[c.id]) return;
      const opcion = aplicarFormatos(opciones[Number(c.dataset.indice)]);
      if (sinAnimacion) opcion.animation = false;
      const g = echarts.init(c, null, { renderer: "canvas" });
      g.setOption(opcion);
      graficos[c.id] = g;
      new ResizeObserver(() => g.resize()).observe(c);
    };
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((entradas) => {
        entradas.forEach((e) => { if (e.isIntersecting) { dibujar(e.target); io.unobserve(e.target); } });
      }, { rootMargin: "200px" });
      contenedores.forEach((c) => io.observe(c));
    } else {
      contenedores.forEach(dibujar);
    }

    document.querySelectorAll(".btn-descargar").forEach((b) => {
      b.addEventListener("click", () => {
        const c = document.getElementById(b.dataset.grafico);
        dibujar(c);
        const titulo = c.closest(".seccion").querySelector("h2").textContent.trim();
        const a = document.createElement("a");
        a.href = graficos[c.id].getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#fff" });
        a.download = titulo + ".png";
        a.click();
      });
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
