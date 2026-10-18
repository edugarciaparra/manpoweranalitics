"""
Catálogo de análisis de cada módulo.

Cada módulo tiene un archivo analisis.py con un Catalogo y sus funciones:

    catalogo = Catalogo()

    @catalogo.registrar("demanda", "Demanda y capacidad",
                        "Cómo evolucionan los pedidos, qué se espera y qué capacidad hace falta.")
    def demanda(periodo):
        return {...}

Cada análisis es profundo: combina en una misma pantalla qué pasó, por qué,
qué se espera y qué conviene hacer. La función recibe el período elegido y
devuelve un dict con:

    kpis          4 indicadores principales
    conclusiones  3 o 4 frases con lo más importante de todo el análisis
    secciones     lista de bloques, cada uno con:
                    titulo, descripcion (opcional)
                    grafico (opción de ECharts, opcional) y grafico_alto
                    lectura   frases que explican el gráfico
                    tabla     (opcional) {titulo, columnas, filas, vacio}
                    acciones  (opcional) lista de {prioridad, titulo, detalle}
    sugerencias   preguntas sugeridas para el asistente
    contexto_ia   datos resumidos que recibe el asistente
"""

PRIORIDADES = {
    "alta": {"texto": "Prioridad alta", "icono": "bi-exclamation-octagon"},
    "media": {"texto": "Prioridad media", "icono": "bi-exclamation-triangle"},
    "baja": {"texto": "Prioridad baja", "icono": "bi-check-circle"},
}


class Catalogo:
    def __init__(self):
        self._analisis = []

    def registrar(self, slug, titulo, descripcion, usa_periodo=True, icono="bi-graph-up"):
        """usa_periodo=False: el análisis muestra la foto de hoy y no tiene selector de período."""
        def decorador(funcion):
            self._analisis.append({
                "slug": slug,
                "titulo": titulo,
                "descripcion": descripcion,
                "usa_periodo": usa_periodo,
                "icono": icono,
                "funcion": funcion,
            })
            return funcion
        return decorador

    def obtener(self, slug):
        for a in self._analisis:
            if a["slug"] == slug:
                return a
        return None

    def __iter__(self):
        return iter(self._analisis)

    def __len__(self):
        return len(self._analisis)


def seccion(titulo, lectura, grafico=None, alto=320, descripcion="", tabla=None, acciones=None):
    """Arma una sección de un análisis. Las acciones quedan con su prioridad lista para mostrar."""
    for a in acciones or []:
        a["prioridad_info"] = PRIORIDADES[a["prioridad"]]
    return {
        "titulo": titulo,
        "descripcion": descripcion,
        "grafico": grafico,
        "grafico_alto": alto,
        "lectura": [l for l in lectura if l],
        "tabla": tabla,
        "acciones": acciones or [],
    }
