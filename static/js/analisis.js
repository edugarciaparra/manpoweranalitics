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
      if (c.dataset.detalle) {
        g.on("click", (p) => {
          if (p.componentType !== "series" || (p.seriesName || "").startsWith("_")) return;
          abrirDetalle(c.dataset.detalle, p.name || "", p.seriesName || "");
        });
      }
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

  // ---------- Detalle de registros (modal) ----------
  const modalEl = document.getElementById("modal-detalle");
  const modal = modalEl ? new bootstrap.Modal(modalEl) : null;
  const POR_PAGINA = 25;
  const det = { columnas: [], filas: [], filtradas: [], pagina: 0, titulo: "", pildoras: {}, texto: "", chip: null };
  const AVATARES = ["#0B5CAB", "#E1251B", "#0E8A5F", "#6A3FD6", "#E07A00", "#0E7C86"];

  function escapar(v) {
    return String(v).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  }

  function pintarDetalle() {
    const total = det.filtradas.length;
    const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));
    det.pagina = Math.min(det.pagina, paginas - 1);
    const desde = det.pagina * POR_PAGINA;
    const visibles = det.filtradas.slice(desde, desde + POR_PAGINA);
    document.getElementById("detalle-cuerpo").innerHTML = visibles
      .map((f) => "<tr>" + f.map((v, i) => "<td>" + celda(det.columnas[i], v) + "</td>").join("") + "</tr>").join("");
    document.getElementById("detalle-vacio").hidden = total > 0;
    document.getElementById("detalle-cuenta").textContent =
      total ? `Mostrando ${desde + 1}–${Math.min(desde + POR_PAGINA, total)} de ${total.toLocaleString("es-UY")} registros` : "";
    document.getElementById("detalle-pagina").textContent = `${det.pagina + 1} / ${paginas}`;
    document.getElementById("detalle-anterior").disabled = det.pagina === 0;
    document.getElementById("detalle-siguiente").disabled = det.pagina >= paginas - 1;
  }

  // Celdas con formato: nombre con iniciales y columnas con pastillas de color
  function celda(columna, v) {
    if (columna === "Nombre" && v) {
      const partes = String(v).split(" ");
      const ini = (partes[0][0] || "") + (partes[1] ? partes[1][0] : "");
      const color = AVATARES[[...String(v)].reduce((a, ch) => a + ch.charCodeAt(0), 0) % AVATARES.length];
      return `<span class="avatar" style="background:${color}">${escapar(ini)}</span><strong>${escapar(v)}</strong>`;
    }
    const mapa = det.pildoras[columna];
    if (mapa && mapa[v]) return `<span class="pildora pildora-${mapa[v]}">${escapar(v)}</span>`;
    return escapar(v);
  }

  function aplicarFiltros() {
    const q = det.texto;
    const iEtapa = det.columnas.indexOf("Etapa");
    det.filtradas = det.filas.filter((f) =>
      (!det.chip || f[iEtapa] === det.chip) &&
      (!q || f.join(" ").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").includes(q)));
    det.pagina = 0;
    document.querySelectorAll(".chip-resumen").forEach((b) => {
      const activo = b.dataset.valor === det.chip;
      b.classList.toggle("activo", activo);
      b.setAttribute("aria-pressed", activo ? "true" : "false");
    });
    pintarDetalle();
  }

  function pintarResumen(resumen) {
    const caja = document.getElementById("detalle-resumen");
    if (!resumen || !resumen.length) { caja.innerHTML = ""; caja.hidden = true; return; }
    caja.hidden = false;
    caja.innerHTML = resumen.map((r) =>
      `<button type="button" class="chip-resumen chip-${r.color}" data-valor="${escapar(r.texto)}" aria-pressed="false">
         <span class="chip-valor">${r.valor.toLocaleString("es-UY")}</span><span class="chip-texto">${escapar(r.texto)}</span>
       </button>`).join("");
    caja.querySelectorAll(".chip-resumen").forEach((b) => b.addEventListener("click", () => {
      det.chip = det.chip === b.dataset.valor ? null : b.dataset.valor;
      aplicarFiltros();
    }));
  }

  async function abrirDetalle(clave, valor, serie) {
    if (!modal) return;
    document.getElementById("detalle-titulo").textContent = "Cargando registros…";
    document.getElementById("detalle-sub").textContent = "";
    document.getElementById("detalle-cabeza").innerHTML = "";
    document.getElementById("detalle-cuerpo").innerHTML = "";
    document.getElementById("detalle-filtro").value = "";
    document.getElementById("detalle-resumen").innerHTML = "";
    det.texto = ""; det.chip = null;
    modal.show();
    const params = new URLSearchParams({ clave, valor, serie, periodo: modalEl.dataset.periodo });
    try {
      const r = await fetch(modalEl.dataset.url + "?" + params);
      const datos = await r.json();
      if (!r.ok) throw new Error(datos.error || "No se pudieron cargar los registros.");
      det.columnas = datos.columnas;
      det.filas = datos.filas;
      det.filtradas = datos.filas;
      det.pagina = 0;
      det.titulo = datos.titulo;
      det.pildoras = datos.pildoras || {};
      pintarResumen(datos.resumen);
      document.getElementById("detalle-titulo").textContent = datos.titulo;
      document.getElementById("detalle-sub").textContent =
        `${datos.total.toLocaleString("es-UY")} registros` + (datos.recortado ? " (se muestran los primeros 2.000)" : "") +
        (datos.descripcion ? " · " + datos.descripcion : "");
      document.getElementById("detalle-cabeza").innerHTML =
        "<tr>" + datos.columnas.map((c) => '<th scope="col">' + escapar(c) + "</th>").join("") + "</tr>";
      pintarDetalle();
    } catch (e) {
      document.getElementById("detalle-titulo").textContent = "No se pudieron cargar los registros";
      document.getElementById("detalle-sub").textContent = e.message + " Cerrá esta ventana y probá de nuevo.";
    }
  }

  if (modalEl) {
    document.getElementById("detalle-filtro").addEventListener("input", (e) => {
      det.texto = e.target.value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      aplicarFiltros();
    });
    document.getElementById("detalle-anterior").addEventListener("click", () => { det.pagina--; pintarDetalle(); });
    document.getElementById("detalle-siguiente").addEventListener("click", () => { det.pagina++; pintarDetalle(); });
    // CSV con ; y BOM para que Excel en español lo abra con columnas y tildes correctas
    document.getElementById("detalle-exportar").addEventListener("click", () => {
      const celda = (v) => '"' + String(v).replace(/"/g, '""') + '"';
      const lineas = [det.columnas, ...det.filtradas].map((f) => f.map(celda).join(";"));
      const blob = new Blob(["\ufeff" + lineas.join("\r\n")], { type: "text/csv;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = (det.titulo || "registros").replace(/[\\/:*?"<>|]/g, "") + ".csv";
      a.click();
      URL.revokeObjectURL(a.href);
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
