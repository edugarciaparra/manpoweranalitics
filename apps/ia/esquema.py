"""
Esquema de la base que se le describe al modelo para que arme las consultas.

Solo se exponen las tablas de TABLAS_PERMITIDAS. Las columnas con datos
personales de candidatos (nombres, documentos, contactos, direcciones) no se
describen y el validador rechaza cualquier consulta que las use.

Las columnas se leen de INFORMATION_SCHEMA de la base (se guardan una hora).
"""
import re

from apps.core.cache import cache_temporal
from apps.core.db import consultar

TABLAS_PERMITIDAS = [
    # Operación
    "Pedidos", "Asignaciones", "Entrevistas", "OrdenesFacturacion", "HistorialViaticos",
    "PedidosPostulante", "CandidatoPruebas", "CandidatoCheckReferencias",
    # Clientes
    "Clientes", "SectoresActividad", "TiposCliente", "EstadosCliente", "Tendencias", "EjecutivosCuenta",
    # Candidatos
    "Candidatos", "CandidatosWeb", "CVExperiencia", "CVFormacion", "CVIdiomas", "CVAptitudes",
    "CandidatosCompetencias", "CandidatosCategoriaProfesional", "PerfilesCandidatos",
    # Tablas de referencia
    "Marcas", "Lineas", "CentrosCosto", "Divisiones", "EstadosPedido", "TiposPedido", "EstadosAsignacion", "TiposAsignacion",
    "Servicios", "Monedas", "Psicologos", "CanalesPublicacionAvisos", "CausalesBaja",
    "Departamentos", "Localidades", "Paises", "EstadosCiviles", "NivelesEducativos",
    "SituacionesLaborales", "Competencias", "CategoriasProfesionales", "CategoriasLibretaConducir",
    "CursosCarreras", "Pruebas", "PracticeAreas", "Problemas", "FormasPago",
]

# Tablas que guardan datos de personas: en ellas se ocultan las columnas personales
TABLAS_PERSONALES = {"Candidatos", "CandidatosWeb", "CVExperiencia", "CVFormacion", "CVIdiomas",
                     "CVAptitudes", "CandidatoCheckReferencias", "PedidosPostulante"}

_PATRON_PERSONAL = re.compile(
    r"nombre|apellido|documento|cedula|^ci$|email|mail|celular|telefono|tel$|direccion|domicilio|"
    r"calle|foto|imagen|^\w*cv$|referente|contacto",
    re.IGNORECASE,
)
# En cualquier tabla
_PATRON_SECRETO = re.compile(r"password|contrase|clave|token|hash", re.IGNORECASE)


def parece_personal(columna):
    return bool(_PATRON_PERSONAL.search(columna) or _PATRON_SECRETO.search(columna))


def es_columna_bloqueada(tabla, columna):
    if _PATRON_SECRETO.search(columna):
        return True
    return tabla in TABLAS_PERSONALES and bool(_PATRON_PERSONAL.search(columna))


_CONSULTA_COLUMNAS = """
SELECT c.[TABLE_NAME] AS Tabla, c.[COLUMN_NAME] AS Columna, c.[DATA_TYPE] AS Tipo
FROM INFORMATION_SCHEMA.COLUMNS c
WHERE c.[TABLE_SCHEMA] = 'dbo' AND c.[TABLE_NAME] IN ({marcas})
ORDER BY c.[TABLE_NAME], c.[ORDINAL_POSITION]
"""


@cache_temporal(segundos=60 * 60)
def columnas_por_tabla():
    """{tabla: [(columna, tipo), ...]} solo con tablas permitidas y sin columnas bloqueadas."""
    sql = _CONSULTA_COLUMNAS.format(marcas=", ".join(["%s"] * len(TABLAS_PERMITIDAS)))
    crudo = {}
    for f in consultar(sql, TABLAS_PERMITIDAS):
        crudo.setdefault(f["Tabla"], []).append((f["Columna"], f["Tipo"]))
    return {t: [(c, tipo) for c, tipo in cols if not es_columna_bloqueada(t, c)]
            for t, cols in crudo.items()}


def columnas_bloqueadas():
    """Nombres de columna (en minúscula) que nunca pueden aparecer en una consulta."""
    sql = _CONSULTA_COLUMNAS.format(marcas=", ".join(["%s"] * len(TABLAS_PERMITIDAS)))
    filas = [(f["Tabla"], f["Columna"]) for f in consultar(sql, TABLAS_PERMITIDAS)]
    return {c.lower() for t, c in filas if es_columna_bloqueada(t, c)}


columnas_bloqueadas = cache_temporal(segundos=60 * 60)(columnas_bloqueadas)


def texto_esquema():
    """Descripción compacta para el modelo: una línea por tabla."""
    lineas = []
    for tabla, cols in sorted(columnas_por_tabla().items()):
        lineas.append(f"{tabla}(" + ", ".join(f"{c} {t}" for c, t in cols) + ")")
    return "\n".join(lineas)
