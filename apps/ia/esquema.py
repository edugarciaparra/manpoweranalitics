"""
Esquema de la base que se le describe al modelo para que arme las consultas.

Solo se exponen las tablas de TABLAS_PERMITIDAS. Las columnas con datos
personales de candidatos (nombres, documentos, contactos, direcciones) no se
describen y el validador rechaza cualquier consulta que las use.

Con la base conectada las columnas se leen de INFORMATION_SCHEMA (se guardan
una hora). Sin conexión se usa ESQUEMA_EJEMPLO, con las columnas que ya
conocemos, para poder probar la pantalla.
"""
import re

from apps.core.cache import cache_temporal
from apps.core.db import consultar, sgo_configurada

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
    "Divisiones", "EstadosPedido", "TiposPedido", "EstadosAsignacion", "TiposAsignacion",
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


ESQUEMA_EJEMPLO = {
    "Clientes": [
        ("ClienteId", "int"), ("ClienteNombre", "varchar"), ("ClienteRazonSocial", "varchar"),
        ("ClienteRUT", "varchar"), ("SectorActividadId", "int"), ("TipoClienteId", "int"),
        ("EstadoClienteId", "int"), ("TendenciaId", "int"), ("ClienteFechaIngreso", "datetime"),
        ("ClienteComprasAnuales", "decimal"), ("ClienteFacturacionAnual", "decimal"),
        ("ClienteCantidadAsociadosManpow", "int"), ("ClienteCantidadAsociadosTotal", "int"),
        ("ClienteOperaAdministrativa", "char"), ("ClienteOperaIndustrial", "char"),
        ("ClienteOperaProfesional", "char"), ("ClienteOperaPromociones", "char"), ("ClienteOperaRPO", "char"),
        ("ClienteUtilizaPersonalTemporal", "char"), ("ClienteRpoEjecutivoId", "int"),
        ("ClientePrmEjecutivoId", "int"), ("ClienteProEjecutivoId", "int"), ("ClienteIndEjecutivoId", "int"),
        ("ClienteAdmEjecutivoId", "int"),
    ],
    "Pedidos": [
        ("PedidoId", "int"), ("PedidoNumero", "int"), ("ClienteId", "int"), ("DivisionId", "int"),
        ("EstadoPedidoId", "int"), ("TipoPedidoId", "int"), ("PerfilCandidatoId", "int"),
        ("PedidoFecha", "datetime"), ("PedidoFechaTopeEntrega", "datetime"),
        ("PedidoFechaEntregaEfectiva", "datetime"), ("PedidoFechaCierre", "datetime"),
        ("PedidoCantidadPersonas", "int"),
    ],
    "Asignaciones": [
        ("AsignacionId", "int"), ("PedidoId", "int"), ("CandidatoId", "int"), ("EstadoAsignacionId", "int"),
        ("TipoAsignacionId", "int"), ("AsignacionEjecutivoId", "int"), ("AsignacionFechaIngreso", "datetime"),
        ("AsignacionFechaEgreso", "datetime"), ("CausalBajaId", "int"),
    ],
    "Entrevistas": [
        ("EntrevistaId", "int"), ("CandidatoId", "int"), ("EntrevistaPedidoId", "int"),
        ("EntrevistaPsicologoId", "int"), ("EntrevistaCanalPublicacion", "int"), ("EntrevistaFecha", "datetime"),
    ],
    "OrdenesFacturacion": [
        ("OrdenId", "int"), ("PedidoId", "int"), ("OrdenFecha", "datetime"), ("OrdenMonto", "decimal"),
        ("OrdenServicioId", "int"), ("OrdenMonCod", "int"), ("OrdenResponsableId", "int"),
    ],
    "HistorialViaticos": [("AsignacionId", "int"), ("ViaticosFecha", "datetime"), ("ViaticosImporte", "decimal")],
    "Candidatos": [
        ("CandidatoId", "int"), ("WebUserId", "int"), ("CandidatoDepartamentoId", "int"),
        ("CandidatoLocalidadId", "int"), ("CandidatoResidenciaId", "int"), ("CandidatoNacionalidadId", "int"),
        ("PerfilCandidatoId", "int"), ("NivelEducativoId", "int"), ("EstadoCivilId", "int"),
        ("SituacionLaboralId", "int"), ("CategoriaLibretaConducirId", "int"),
    ],
    "CandidatosWeb": [
        ("WebUserId", "int"), ("WebUserNombre", "varchar"), ("WebUserApellido", "varchar"),
        ("WebUserNroDocumento", "varchar"), ("WebUserEmail", "varchar"), ("WebUserCelular", "varchar"),
        ("WebUserCv", "varchar"), ("DepartamentoId", "int"), ("LocalidadId", "int"), ("WebUserSexo", "char"),
        ("WebUserFechaNacimiento", "datetime"), ("WebUserSalarioActual", "decimal"),
        ("WebUserSalarioAspirado", "decimal"), ("WebUserSalarioAspiradoMoneda", "int"),
        ("WebUserDisponibilidadHoraria", "char"), ("WebUserHorarioRotativo", "char"), ("WebUserZafrales", "char"),
        ("WebUserLibretaConducir", "char"), ("WebUserEstadoCivilId", "int"), ("WebUserFechaAct", "datetime"),
    ],
    "CVExperiencia": [
        ("WebUserId", "int"), ("CVExpId", "int"), ("CVExpEmpresa", "varchar"), ("CVExpCargo", "varchar"),
        ("CVExpFechaIngreso", "datetime"), ("CVExpFechaEgreso", "datetime"), ("CVExpTrabajoActual", "char"),
        ("CausalBajaId", "int"),
    ],
    "CVFormacion": [
        ("WebUserId", "int"), ("CVFormId", "int"), ("CursoId", "int"), ("CVFormCompleto", "char"),
        ("CVFormInstitucion", "varchar"), ("CVFormFechaInicio", "datetime"), ("CVFormFechaFin", "datetime"),
    ],
    "CVIdiomas": [("WebUserId", "int"), ("CVIdiomaId", "int"), ("CVIdiomaNivel", "int"), ("CVIdiomaAniosExp", "int")],
    "SectoresActividad": [("SectorActividadId", "int"), ("SectorActividadDescripcion", "varchar")],
    "TiposCliente": [("TipoClienteId", "int"), ("TipoClienteDescripcion", "varchar")],
    "EstadosCliente": [("EstadoClienteId", "int"), ("EstadoClienteDescripcion", "varchar")],
    "Tendencias": [("TendenciaId", "int"), ("TendenciaDescripcion", "varchar")],
    "EjecutivosCuenta": [("EjecutivoCuentaId", "int"), ("EjecutivoCuentaNombre", "varchar"),
                         ("EjecutivoCuentaApellido", "varchar"), ("EjecutivoCuentaEstado", "char")],
    "Divisiones": [("DivisionId", "int"), ("DivisionDescripcion", "varchar")],
    "EstadosPedido": [("EstadoPedidoId", "int"), ("EstadoPedidoDescripcion", "varchar")],
    "TiposPedido": [("TipoPedidoId", "int"), ("TipoPedidoDescripcion", "varchar")],
    "EstadosAsignacion": [("EstadoAsignacionId", "int"), ("EstadoAsignacionDescripcion", "varchar")],
    "Servicios": [("ServicioId", "int"), ("ServicioDescripcion", "varchar")],
    "Monedas": [("moncod", "int"), ("mondsc", "varchar")],
    "Psicologos": [("PsicologoId", "int"), ("PsicologoNombre", "varchar"), ("PsicologoApellido", "varchar")],
    "CanalesPublicacionAvisos": [("CanalPublicacionId", "int"), ("CanalPublicacionDescripcion", "varchar")],
    "CausalesBaja": [("CausalBajaId", "int"), ("CausalBajaDescripcion", "varchar")],
    "Departamentos": [("DepartamentoId", "int"), ("DepartamentoNombre", "varchar")],
    "Localidades": [("LocalidadId", "int"), ("LocalidadNombre", "varchar")],
    "EstadosCiviles": [("EstadoCivilId", "int"), ("EstadoCivilDescripcion", "varchar")],
    "NivelesEducativos": [("NivelEducativoId", "int"), ("NivelEducativoDescripcion", "varchar")],
    "CursosCarreras": [("CursoId", "int"), ("CursoNombre", "varchar"), ("NivelEducativoId", "int")],
    "Competencias": [("CompetenciaId", "int"), ("CompetenciaNombre", "varchar")],
}

_CONSULTA_COLUMNAS = """
SELECT c.[TABLE_NAME] AS Tabla, c.[COLUMN_NAME] AS Columna, c.[DATA_TYPE] AS Tipo
FROM INFORMATION_SCHEMA.COLUMNS c
WHERE c.[TABLE_SCHEMA] = 'dbo' AND c.[TABLE_NAME] IN ({marcas})
ORDER BY c.[TABLE_NAME], c.[ORDINAL_POSITION]
"""


@cache_temporal(segundos=60 * 60)
def columnas_por_tabla():
    """{tabla: [(columna, tipo), ...]} solo con tablas permitidas y sin columnas bloqueadas."""
    if sgo_configurada():
        sql = _CONSULTA_COLUMNAS.format(marcas=", ".join(["%s"] * len(TABLAS_PERMITIDAS)))
        crudo = {}
        for f in consultar(sql, TABLAS_PERMITIDAS):
            crudo.setdefault(f["Tabla"], []).append((f["Columna"], f["Tipo"]))
    else:
        crudo = ESQUEMA_EJEMPLO
    return {t: [(c, tipo) for c, tipo in cols if not es_columna_bloqueada(t, c)]
            for t, cols in crudo.items()}


def columnas_bloqueadas():
    """Nombres de columna (en minúscula) que nunca pueden aparecer en una consulta."""
    if sgo_configurada():
        sql = _CONSULTA_COLUMNAS.format(marcas=", ".join(["%s"] * len(TABLAS_PERMITIDAS)))
        filas = [(f["Tabla"], f["Columna"]) for f in consultar(sql, TABLAS_PERMITIDAS)]
    else:
        filas = [(t, c) for t, cols in ESQUEMA_EJEMPLO.items() for c, _ in cols]
    return {c.lower() for t, c in filas if es_columna_bloqueada(t, c)}


columnas_bloqueadas = cache_temporal(segundos=60 * 60)(columnas_bloqueadas)


def texto_esquema():
    """Descripción compacta para el modelo: una línea por tabla."""
    lineas = []
    for tabla, cols in sorted(columnas_por_tabla().items()):
        lineas.append(f"{tabla}(" + ", ".join(f"{c} {t}" for c, t in cols) + ")")
    return "\n".join(lineas)
