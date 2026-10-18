"""
Catálogo de análisis de cada módulo.

Cada módulo tiene un archivo analisis.py con un Catalogo y sus funciones:

    catalogo = Catalogo()

    @catalogo.registrar("descriptivo", "evolucion", "Evolución de pedidos",
                        "Altas y cierres de los últimos 12 meses.")
    def evolucion(periodo):
        return {...}

Cada función recibe el período elegido y devuelve un dict con:
    kpis        lista de {label, valor, detalle, alerta}
    grafico     opción de ECharts (dict)
    lectura     lista de frases con lo que muestran los datos
    acciones    (opcional) lista de {prioridad, titulo, detalle}
    tabla       (opcional) {titulo, columnas, filas, vacio}
    sugerencias preguntas sugeridas para el asistente
    contexto_ia datos resumidos que recibe el asistente
"""

TIPOS = {
    "descriptivo": {
        "titulo": "Descriptivo",
        "pregunta": "¿Qué pasó?",
        "icono": "bi-bar-chart-line",
        "explicacion": "Cómo están los números hoy y cómo evolucionaron.",
    },
    "diagnostico": {
        "titulo": "Diagnóstico",
        "pregunta": "¿Por qué pasó?",
        "icono": "bi-search",
        "explicacion": "Qué explica los resultados: dónde se concentran y qué los mueve.",
    },
    "predictivo": {
        "titulo": "Predictivo",
        "pregunta": "¿Qué va a pasar?",
        "icono": "bi-graph-up-arrow",
        "explicacion": "Proyecciones y probabilidades a partir de la historia.",
    },
    "prescriptivo": {
        "titulo": "Prescriptivo",
        "pregunta": "¿Qué conviene hacer?",
        "icono": "bi-signpost-split",
        "explicacion": "Qué acciones tomar y en qué orden.",
    },
}

PRIORIDADES = {
    "alta": {"texto": "Prioridad alta", "icono": "bi-exclamation-octagon"},
    "media": {"texto": "Prioridad media", "icono": "bi-exclamation-triangle"},
    "baja": {"texto": "Prioridad baja", "icono": "bi-check-circle"},
}


class Catalogo:
    def __init__(self):
        self._analisis = []

    def registrar(self, tipo, slug, titulo, descripcion, usa_periodo=True):
        """usa_periodo=False: el análisis muestra la foto de hoy y no tiene selector de período."""
        if tipo not in TIPOS:
            raise ValueError(f"Tipo de análisis desconocido: {tipo}")

        def decorador(funcion):
            self._analisis.append({
                "tipo": tipo,
                "slug": slug,
                "titulo": titulo,
                "descripcion": descripcion,
                "usa_periodo": usa_periodo,
                "funcion": funcion,
            })
            return funcion
        return decorador

    def obtener(self, slug):
        for a in self._analisis:
            if a["slug"] == slug:
                return a
        return None

    def por_tipo(self):
        """[(tipo_slug, tipo_info, [analisis...]), ...] en el orden de TIPOS."""
        return [
            (t, info, [a for a in self._analisis if a["tipo"] == t])
            for t, info in TIPOS.items()
        ]

    def __iter__(self):
        return iter(self._analisis)
