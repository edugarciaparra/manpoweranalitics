// Preguntale a Rafa: conversación con gráfico (de tipo intercambiable) y datos, preguntas sugeridas y preguntas anteriores.
(function () {
  const raiz = document.getElementById("rafa-chat");
  if (!raiz) return;
  const form = document.getElementById("nl-form");
  const texto = document.getElementById("nl-pregunta");
  const enviar = document.getElementById("nl-enviar");
  const conversacion = document.getElementById("nl-conversacion");
  const bienvenida = document.getElementById("nl-bienvenida");
  const listaHistorial = document.getElementById("nl-historial");
  const historialVacio = document.getElementById("nl-historial-vacio");
  const plantilla = document.getElementById("nl-plantilla");
  const csrf = raiz.querySelector("[name=csrfmiddlewaretoken]").value;
  const modulo = raiz.dataset.modulo || "";
  const FILAS_POR_PAGINA = 20;
  const nf = new Intl.NumberFormat("es-UY", { maximumFractionDigits: 2 });
  const nfCorto = new Intl.NumberFormat("es-UY", { maximumFractionDigits: 1 });
  const graficos = [];

  const escapar = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const normalizar = (t) => String(t ?? "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const formatoValor = (v) => (typeof v === "number" ? nf.format(v) : v ?? "");

  // ---------- Formatos de ECharts ----------
  const formatos = { "fmt:num": (v) => (v == null ? "–" : nfCorto.format(v)) };
  function aplicarFormatos(obj) {
    if (Array.isArray(obj)) return obj.map(aplicarFormatos);
    if (obj && typeof obj === "object") {
      const copia = {};
      for (const k of Object.keys(obj)) copia[k] = aplicarFormatos(obj[k]);
      return copia;
    }
    return typeof obj === "string" && formatos[obj] ? formatos[obj] : obj;
  }

  // Respuesta: párrafos y líneas "- " como lista
  function pintarTexto(el, contenido) {
    const bloques = [];
    let lista = null;
    String(contenido || "").split(/\n/).forEach((linea) => {
      const l = linea.trim();
      if (!l) { lista = null; return; }
      if (/^[-•*]\s+/.test(l)) {
        if (!lista) { lista = []; bloques.push(lista); }
        lista.push(l.replace(/^[-•*]\s+/, ""));
      } else {
        lista = null;
        bloques.push(l);
      }
    });
    const negrita = (t) => escapar(t).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    el.innerHTML = bloques.map((b) => Array.isArray(b)
      ? "<ul>" + b.map((i) => "<li>" + negrita(i) + "</li>").join("") + "</ul>"
      : "<p>" + negrita(b) + "</p>").join("");
  }

  function exportar(columnas, filas, nombre) {
    const celda = (v) => '"' + String(v ?? "").replace(/"/g, '""') + '"';
    const lineas = [columnas, ...filas].map((f) => f.map(celda).join(";"));
    const blob = new Blob(["﻿" + lineas.join("\r\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = (nombre || "consulta").replace(/[\\/:*?"<>|]/g, "").slice(0, 80) + ".csv";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function armarTabla(turno, columnas, filas) {
    const thead = turno.querySelector("thead");
    const tbody = turno.querySelector("tbody");
    const numericas = columnas.map((_, i) => filas.some((f) => typeof f[i] === "number"));
    const estado = { filtradas: filas, pagina: 0 };
    thead.innerHTML = "<tr>" + columnas.map((c, i) =>
      `<th scope="col"${numericas[i] ? ' class="text-end"' : ""}>${escapar(c)}</th>`).join("") + "</tr>";
    const pintar = () => {
      const paginas = Math.max(1, Math.ceil(estado.filtradas.length / FILAS_POR_PAGINA));
      estado.pagina = Math.min(Math.max(0, estado.pagina), paginas - 1);
      const desde = estado.pagina * FILAS_POR_PAGINA;
      tbody.innerHTML = estado.filtradas.slice(desde, desde + FILAS_POR_PAGINA).map((f) =>
        "<tr>" + f.map((v, i) => `<td${numericas[i] ? ' class="text-end"' : ""}>${escapar(formatoValor(v))}</td>`).join("") + "</tr>"
      ).join("") || `<tr><td colspan="${columnas.length}" class="vacio">No hay filas que coincidan.</td></tr>`;
      turno.querySelector(".nl-cuenta").textContent =
        `${estado.filtradas.length.toLocaleString("es-UY")} de ${filas.length.toLocaleString("es-UY")} filas`;
      turno.querySelector(".nl-pagina").textContent = `${estado.pagina + 1} / ${paginas}`;
      turno.querySelector(".nl-paginado").hidden = paginas < 2;
    };
    turno.querySelector(".nl-filtro").addEventListener("input", (e) => {
      const q = normalizar(e.target.value);
      estado.filtradas = q ? filas.filter((f) => f.some((v) => normalizar(v).includes(q))) : filas;
      estado.pagina = 0;
      pintar();
    });
    turno.querySelectorAll(".nl-paginado [data-paso]").forEach((b) =>
      b.addEventListener("click", () => { estado.pagina += Number(b.dataset.paso); pintar(); }));
    pintar();
    return estado;
  }

  function mostrarVista(turno, vista) {
    turno.querySelectorAll(".nl-pestanas [data-vista]").forEach((b) => {
      const activa = b.dataset.vista === vista;
      b.classList.toggle("activa", activa);
      b.setAttribute("aria-selected", activa);
    });
    turno.querySelectorAll(".nl-vista").forEach((v) => (v.hidden = v.dataset.vista !== vista));
    turno.querySelector(".nl-tipos").hidden = vista !== "grafico";
    if (vista === "grafico") graficos.forEach((g) => g.resize());
  }

  // Gráfico con botones para cambiar de tipo (columnas, barras, líneas, torta)
  function armarGrafico(turno, datosGraficos) {
    const cont = turno.querySelector(".nl-grafico");
    const tipos = turno.querySelector(".nl-tipos");
    const g = echarts.init(cont, null, { renderer: "canvas" });
    graficos.push(g);
    const dibujar = (tipo) => {
      const opcion = aplicarFormatos(datosGraficos.opciones[tipo]);
      cont.style.height = (opcion._alto || 320) + "px";
      delete opcion._alto;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) opcion.animation = false;
      g.setOption(opcion, true);
      g.resize();
      tipos.querySelectorAll("button").forEach((b) => b.classList.toggle("activo", b.dataset.tipo === tipo));
    };
    const disponibles = Object.keys(datosGraficos.opciones);
    tipos.innerHTML = disponibles.length > 1 ? disponibles.map((t) =>
      `<button type="button" data-tipo="${t}">${escapar(datosGraficos.nombres[t] || t)}</button>`).join("") : "";
    tipos.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => dibujar(b.dataset.tipo)));
    dibujar(datosGraficos.principal);
  }

  function pintarResultado(turno, datos) {
    const tarjeta = turno.querySelector(".nl-tarjeta");
    if (datos.id) turno.dataset.id = datos.id;
    if (datos.error || datos.tipo === "error") {
      tarjeta.classList.add("nl-error");
      turno.querySelector(".nl-tarjeta-titulo").textContent = "No pude responder esa pregunta";
      turno.querySelector(".nl-respuesta").innerHTML = "<p>" + escapar(datos.error || "Ocurrió un error.") +
        "</p><p class='nl-pista'>Probá reformularla con más detalle: qué dato, de qué período y agrupado por qué.</p>";
      return;
    }
    turno.querySelector(".nl-tarjeta-titulo").textContent =
      datos.titulo || (datos.tipo === "aclaracion" ? "Necesito un dato más" : "Respuesta");
    const meta = [];
    if (datos.fecha) meta.push(datos.fecha);
    if (datos.filas) meta.push(`${datos.filas.length.toLocaleString("es-UY")} filas` + (datos.recortado ? " (recortado)" : ""));
    if (datos.segundos != null) meta.push(`${nfCorto.format(datos.segundos)} s`);
    turno.querySelector(".nl-meta").textContent = meta.join(" · ");
    pintarTexto(turno.querySelector(".nl-respuesta"), datos.respuesta);
    if (datos.tipo === "aclaracion") tarjeta.classList.add("nl-aclaracion");

    const tieneDatos = Array.isArray(datos.filas) && datos.filas.length > 0;
    if (!tieneDatos) return;
    const tieneGrafico = datos.graficos && datos.graficos.opciones && typeof echarts !== "undefined";
    turno.querySelector(".nl-vistas").hidden = false;
    turno.querySelector('[data-vista="grafico"]').hidden = !tieneGrafico;

    const estadoTabla = armarTabla(turno, datos.columnas, datos.filas);
    mostrarVista(turno, tieneGrafico ? "grafico" : "tabla");
    if (tieneGrafico) armarGrafico(turno, datos.graficos);

    turno.querySelectorAll(".nl-pestanas [data-vista]").forEach((b) =>
      b.addEventListener("click", () => mostrarVista(turno, b.dataset.vista)));
    turno.querySelector('[data-accion="exportar"]').addEventListener("click", () =>
      exportar(datos.columnas, estadoTabla.filtradas, datos.titulo || datos.pregunta));
  }

  function nuevoTurno(pregunta) {
    bienvenida.hidden = true;
    const turno = plantilla.content.firstElementChild.cloneNode(true);
    turno.querySelector(".nl-yo").textContent = pregunta;
    conversacion.appendChild(turno);
    return turno;
  }

  // ---------- Preguntas anteriores (menú del costado) ----------
  function agregarAlHistorial(id, pregunta, conError) {
    if (!id) return;
    historialVacio.hidden = true;
    const li = document.createElement("li");
    const ahora = new Date();
    const fecha = ahora.toLocaleDateString("es-UY", { day: "2-digit", month: "2-digit" }) + " " +
      ahora.toLocaleTimeString("es-UY", { hour: "2-digit", minute: "2-digit" });
    li.innerHTML = `<button type="button" class="rafa-item rafa-hist actual${conError ? " con-error" : ""}" data-id="${id}">` +
      `<span class="rafa-hist-texto">${escapar(pregunta)}</span><span class="rafa-hist-fecha">${fecha}</span></button>`;
    listaHistorial.prepend(li);
    li.querySelector("button").addEventListener("click", () => abrirAnterior(li.querySelector("button")));
  }

  async function abrirAnterior(boton) {
    const id = boton.dataset.id;
    const existente = conversacion.querySelector(`.nl-turno[data-id="${id}"]`);
    if (existente) {
      existente.scrollIntoView({ behavior: "smooth", block: "start" });
      existente.classList.add("resaltado");
      setTimeout(() => existente.classList.remove("resaltado"), 1600);
      return;
    }
    const turno = nuevoTurno(boton.querySelector(".rafa-hist-texto").textContent);
    turno.classList.add("anterior");
    turno.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const r = await fetch(raiz.dataset.urlConsulta.replace(/0\/$/, id + "/"));
      const datos = await r.json();
      if (!r.ok) throw new Error(datos.error || "No se encontró esa pregunta.");
      pintarResultado(turno, datos);
    } catch (e) {
      pintarResultado(turno, { error: e.message });
    }
  }

  async function preguntar(pregunta) {
    const turno = nuevoTurno(pregunta);
    turno.scrollIntoView({ behavior: "smooth", block: "start" });
    enviar.disabled = true;
    let datos = {};
    try {
      const r = await fetch(raiz.dataset.url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({ pregunta, modulo }),
      });
      datos = await r.json().catch(() => ({}));
      if (!r.ok) datos = { error: datos.error || "No se pudo responder. Probá de nuevo.", id: datos.id };
    } catch (e) {
      datos = { error: "No hay conexión con el servidor." };
    } finally {
      enviar.disabled = false;
      texto.focus();
    }
    pintarResultado(turno, datos);
    agregarAlHistorial(datos.id, pregunta, !!datos.error);
  }

  // ---------- Eventos ----------
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const p = texto.value.trim();
    if (!p || enviar.disabled) return;
    texto.value = "";
    texto.style.height = "";
    preguntar(p);
  });
  texto.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });
  texto.addEventListener("input", () => {
    texto.style.height = "";
    texto.style.height = Math.min(texto.scrollHeight, 160) + "px";
  });
  raiz.querySelectorAll(".nl-sugerencia").forEach((b) =>
    b.addEventListener("click", () => { if (!enviar.disabled) preguntar(b.dataset.pregunta); }));
  listaHistorial.querySelectorAll(".rafa-hist").forEach((b) => b.addEventListener("click", () => abrirAnterior(b)));
  document.getElementById("nl-nueva").addEventListener("click", async () => {
    try {
      await fetch(raiz.dataset.urlNueva, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({ modulo }),
      });
    } catch (e) { /* sin conexión: igual se limpia la pantalla */ }
    graficos.splice(0).forEach((g) => g.dispose());
    conversacion.innerHTML = "";
    bienvenida.hidden = false;
    listaHistorial.querySelectorAll(".rafa-hist.actual").forEach((b) => b.classList.remove("actual"));
    texto.focus();
  });
  window.addEventListener("resize", () => graficos.forEach((g) => g.resize()));

  // Conversación en curso (se conserva al recargar o volver a la página)
  const guardados = JSON.parse(document.getElementById("nl-turnos").textContent || "[]");
  guardados.forEach((t) => pintarResultado(nuevoTurno(t.pregunta), t));
  if (guardados.length) conversacion.lastElementChild.scrollIntoView({ block: "start" });

  if (raiz.dataset.inicial) {
    history.replaceState(null, "", location.pathname);
    preguntar(raiz.dataset.inicial);
  }
})();
