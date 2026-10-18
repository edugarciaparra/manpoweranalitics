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
                    explicacion  cómo leer el gráfico (qué muestra cada eje, color, etc.)
                    lectura   frases con lo que muestran los datos
                    detalle   (opcional) clave para ver los registros al hacer clic
                    tabla     (opcional) {titulo, columnas, filas, vacio}
    sugerencias   preguntas sugeridas para el asistente
    contexto_ia   datos resumidos que recibe el asistente

Detalle de registros: si una sección tiene detalle="clave", al hacer clic en el
gráfico se abre un modal con los registros. Los arma la función registrada con

    @catalogo.detalle("mi-analisis")
    def detalle(clave, valor, serie, periodo):
        return {"titulo": ..., "columnas": [...], "filas": [[...], ...]}

donde valor es la categoría cliqueada (barra, sector, mes) y serie el nombre de la serie.
Si el análisis tiene filtros, la función de detalle recibe además filtros=... .

KPIs: {"label", "valor", "detalle" (opcional), "alerta" (opcional), "ayuda" (opcional, cómo se calcula)}.
"""

PRIORIDADES = {
    "alta": {"texto": "Prioridad alta", "icono": "bi-exclamation-octagon"},
    "media": {"texto": "Prioridad media", "icono": "bi-exclamation-triangle"},
    "baja": {"texto": "Prioridad baja", "icono": "bi-check-circle"},
}


class Catalogo:
    def __init__(self):
        self._analisis = []
        self._detalles = {}

    def registrar(self, slug, titulo, descripcion, usa_periodo=True, icono="bi-graph-up",
                  periodos=None, periodo_defecto=None, filtros=None):
        """usa_periodo=False: el análisis muestra la foto de hoy y no tiene selector de período.
        periodos / periodo_defecto: opciones propias de período, si no sirven las comunes.
        filtros: lista de apps.core.filtros.Filtro; la función recibe (periodo, filtros)."""
        def decorador(funcion):
            self._analisis.append({
                "slug": slug,
                "titulo": titulo,
                "descripcion": descripcion,
                "usa_periodo": usa_periodo,
                "icono": icono,
                "periodos": periodos,
                "periodo_defecto": periodo_defecto,
                "filtros": filtros or [],
                "funcion": funcion,
            })
            return funcion
        return decorador

    def detalle(self, slug):
        """Registra la función que devuelve los registros detrás de un gráfico del análisis."""
        def decorador(funcion):
            self._detalles[slug] = funcion
            return funcion
        return decorador

    def obtener_detalle(self, slug):
        return self._detalles.get(slug)

    def obtener(self, slug):
        for a in self._analisis:
            if a["slug"] == slug:
                return a
        return None

    def __iter__(self):
        return iter(self._analisis)

    def __len__(self):
        return len(self._analisis)


def seccion(titulo, lectura, grafico=None, alto=320, descripcion="", tabla=None, acciones=None,
            explicacion="", detalle=None, ayuda_detalle=""):
    """Arma una sección de un análisis. Las acciones quedan con su prioridad lista para mostrar."""
    # Las acciones recomendadas no se muestran: las va a generar el asistente de IA.
    acciones = []
    return {
        "titulo": titulo,
        "descripcion": descripcion,
        "grafico": grafico,
        "grafico_alto": alto,
        "lectura": [l for l in lectura if l],
        "tabla": tabla,
        "acciones": acciones or [],
        "explicacion": explicacion,
        "detalle": detalle,
        "ayuda_detalle": ayuda_detalle or "Hacé clic en el gráfico para ver los registros.",
    }
