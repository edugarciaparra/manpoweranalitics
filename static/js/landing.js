// Landing: saludo según la hora y filtro de módulos mientras se escribe.
(function () {
  const saludo = document.getElementById("saludo");
  if (saludo) {
    const h = new Date().getHours();
    const momento = h < 12 ? "Buen día" : h < 20 ? "Buenas tardes" : "Buenas noches";
    saludo.textContent = saludo.textContent.replace(/^Hola/, momento);
  }

  const input = document.getElementById("buscar");
  const form = document.getElementById("buscador");
  const columnas = Array.from(document.querySelectorAll(".modulo-col"));
  const sinResultados = document.getElementById("sin-resultados");

  // Saca tildes para que "facturacion" encuentre "Facturación"
  const normalizar = (t) => t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

  function visibles() {
    return columnas.filter((c) => !c.hidden);
  }

  function filtrar() {
    const palabras = normalizar(input.value).split(/\s+/).filter(Boolean);
    columnas.forEach((col) => {
      const texto = normalizar(col.dataset.buscar);
      col.hidden = !palabras.every((p) => texto.includes(p));
      col.querySelector(".modulo").classList.remove("destacado");
    });
    const v = visibles();
    if (palabras.length && v.length) v[0].querySelector(".modulo").classList.add("destacado");
    sinResultados.hidden = v.length > 0;
  }

  input.addEventListener("input", filtrar);
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const primero = visibles()[0];
    if (primero) window.location = primero.querySelector(".modulo").href;
  });
  // Atajo: "/" enfoca el buscador
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== input) {
      e.preventDefault();
      input.focus();
    }
  });
})();
