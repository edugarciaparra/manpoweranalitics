// Consultas en lenguaje natural: conversación, gráfico, tabla y SQL de cada respuesta.
(function () {
  const form = document.getElementById("nl-form");
  const texto = document.getElementById("nl-pregunta");
  const enviar = document.getElementById("nl-enviar");
  const conversacion = document.getElementById("nl-conversacion");
  const sugerencias = document.getElementById("nl-sugerencias");
  const plantilla = document.getElementById("nl-plantilla");
  const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;
  const FILAS_POR_PAGINA = 25;
  const nf = new Intl.NumberFormat("es-UY", { maximumFractionDigits: 2 });
  const nfCorto = new Intl.NumberFormat("es-UY", { maximumFractionDigits: 1 });

  // Preguntas anteriores con su SQL, para entender las repreguntas
  let historial = [];
  const graficos = [];

  const escapar = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const normalizar = (t) => String(t ?? "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  const formatoValor = (v) => (typeof v === "number" ? nf.format(v) : v ?? "");

  // ---------- Formatos de ECharts ----------
  const formatos = { "fmt:num": (v) => (v == null ? "–" : nfCorto.format(v)) };
  function aplicarFormatos(obj) {
    if (Array.isArray(obj)) return obj.map(aplicarFormatos);
    if (obj && typeof obj === "object") {
      for (const k of Object.keys(obj)) obj[k] = aplicarFormatos(obj[k]);
      return obj;
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
    if (vista === "grafico") graficos.forEach((g) => g.resize());
  }

  function pintarResultado(turno, datos) {
    const tarjeta = turno.querySelector(".nl-tarjeta");
    turno.querySelector(".nl-tarjeta-titulo").textContent =
      datos.titulo || (datos.tipo === "aclaracion" ? "Necesito un dato más" : "Respuesta");
    const meta = [];
    if (datos.filas) meta.push(`${datos.filas.length.toLocaleString("es-UY")} filas` + (datos.recortado ? " (recortado)" : ""));
    if (datos.segundos != null) meta.push(`${nfCorto.format(datos.segundos)} s`);
    turno.querySelector(".nl-meta").textContent = meta.join(" · ");
    pintarTexto(turno.querySelector(".nl-respuesta"), datos.respuesta);
    if (datos.tipo === "aclaracion") tarjeta.classList.add("nl-aclaracion");

    if (!datos.sql) return;
    const vistas = turno.querySelector(".nl-vistas");
    vistas.hidden = false;
    turno.querySelector(".nl-explicacion").textContent = datos.explicacion || "";
    turno.querySelector(".nl-sql code").textContent = datos.sql;

    const tieneDatos = Array.isArray(datos.filas) && datos.filas.length > 0;
    const tieneGrafico = tieneDatos && datos.grafico && typeof echarts !== "undefined";
    turno.querySelector('[data-vista="grafico"]').hidden = !tieneGrafico;
    turno.querySelector('.nl-pestanas [data-vista="tabla"]').hidden = !tieneDatos;
    turno.querySelector('[data-accion="exportar"]').hidden = !tieneDatos;

    let estadoTabla = null;
    if (tieneDatos) estadoTabla = armarTabla(turno, datos.columnas, datos.filas);
    mostrarVista(turno, tieneGrafico ? "grafico" : tieneDatos ? "tabla" : "sql");

    if (tieneGrafico) {
      const opcion = aplicarFormatos(datos.grafico);
      const cont = turno.querySelector(".nl-grafico");
      cont.style.height = (opcion._alto || 340) + "px";
      delete opcion._alto;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) opcion.animation = false;
      const g = echarts.init(cont, null, { renderer: "canvas" });
      g.setOption(opcion);
      graficos.push(g);
    }

    turno.querySelectorAll(".nl-pestanas [data-vista]").forEach((b) =>
      b.addEventListener("click", () => mostrarVista(turno, b.dataset.vista)));
    turno.querySelector('[data-accion="exportar"]').addEventListener("click", () =>
      exportar(datos.columnas, estadoTabla ? estadoTabla.filtradas : datos.filas, datos.titulo));
    const copiar = turno.querySelector('[data-accion="copiar"]');
    copiar.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(datos.sql);
        copiar.innerHTML = '<i class="bi bi-check2" aria-hidden="true"></i> Copiado';
      } catch (e) {
        copiar.textContent = "No se pudo copiar";
      }
      setTimeout(() => (copiar.innerHTML = '<i class="bi bi-clipboard" aria-hidden="true"></i> Copiar SQL'), 1800);
    });
  }

  async function preguntar(pregunta) {
    sugerencias.hidden = true;
    const turno = plantilla.content.firstElementChild.cloneNode(true);
    turno.querySelector(".nl-yo").textContent = pregunta;
    conversacion.appendChild(turno);
    turno.scrollIntoView({ behavior: "smooth", block: "start" });
    enviar.disabled = true;
    try {
      const r = await fetch(form.dataset.url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({ pregunta, historial, modulo: form.dataset.modulo || "" }),
      });
      const datos = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(datos.error || "No se pudo responder. Probá de nuevo.");
      pintarResultado(turno, datos);
      if (datos.sql) historial = [...historial, { pregunta, sql: datos.sql }].slice(-4);
    } catch (e) {
      turno.querySelector(".nl-tarjeta").classList.add("nl-error");
      turno.querySelector(".nl-tarjeta-titulo").textContent = "No pude responder esa pregunta";
      turno.querySelector(".nl-respuesta").innerHTML =
        "<p>" + escapar(e.message === "Failed to fetch" ? "No hay conexión con el servidor." : e.message) +
        "</p><p class='nl-pista'>Probá reformularla con más detalle: qué dato, de qué período y agrupado por qué.</p>";
    } finally {
      enviar.disabled = false;
      texto.focus();
    }
  }

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
  document.querySelectorAll(".nl-sugerencia").forEach((b) =>
    b.addEventListener("click", () => preguntar(b.dataset.pregunta)));
  document.getElementById("nl-nueva").addEventListener("click", () => {
    historial = [];
    graficos.splice(0).forEach((g) => g.dispose());
    conversacion.innerHTML = "";
    sugerencias.hidden = false;
    texto.focus();
  });
  window.addEventListener("resize", () => graficos.forEach((g) => g.resize()));

  if (form.dataset.inicial) preguntar(form.dataset.inicial);
})();
