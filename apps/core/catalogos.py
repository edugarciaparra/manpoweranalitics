"""
Tablas de referencia de sgo_new (Id -> descripción).

Las descripciones nunca se escriben en el código de los análisis: salen de estas
tablas. Con la base conectada se leen con SQL; sin conexión se usan tablas de
ejemplo con la misma estructura, solo para poder desarrollar la interfaz.

    catalogo("CausalesBaja")        {CausalBajaId: CausalBajaDescripcion}
    catalogo("NivelesEducativos")   {NivelEducativoId: NivelEducativoDescripcion} (ordenado por Id)
    cursos()                        {CursoId: (CursoNombre, NivelEducativoId)}
"""
from .cache import cache_temporal
from .db import consultar, sgo_configurada

CONSULTAS = {
    "CausalesBaja": "SELECT [CausalBajaId] AS Id, [CausalBajaDescripcion] AS Descripcion FROM [CausalesBaja]",
    "NivelesEducativos": "SELECT [NivelEducativoId] AS Id, [NivelEducativoDescripcion] AS Descripcion "
                         "FROM [NivelesEducativos] ORDER BY [NivelEducativoId]",
    "Departamentos": "SELECT [DepartamentoId] AS Id, [DepartamentoNombre] AS Descripcion FROM [Departamentos]",
    "Localidades": "SELECT [LocalidadId] AS Id, [LocalidadNombre] AS Descripcion FROM [Localidades]",
    "EstadosCiviles": "SELECT [EstadoCivilId] AS Id, [EstadoCivilDescripcion] AS Descripcion FROM [EstadosCiviles]",
    # Clientes. Nombres de columna de descripción a confirmar con INFORMATION_SCHEMA
    "SectoresActividad": "SELECT [SectorActividadId] AS Id, [SectorActividadDescripcion] AS Descripcion FROM [SectoresActividad]",
    "TiposCliente": "SELECT [TipoClienteId] AS Id, [TipoClienteDescripcion] AS Descripcion FROM [TiposCliente]",
    "EstadosCliente": "SELECT [EstadoClienteId] AS Id, [EstadoClienteDescripcion] AS Descripcion FROM [EstadosCliente]",
    "Tendencias": "SELECT [TendenciaId] AS Id, [TendenciaDescripcion] AS Descripcion FROM [Tendencias]",
    "EjecutivosCuenta": "SELECT [EjecutivoCuentaId] AS Id, [EjecutivoCuentaNombre] AS Descripcion FROM [EjecutivosCuenta]",
    # Solo las competencias que se usan como idioma en los CV
    "Idiomas": "SELECT DISTINCT c.[CompetenciaId] AS Id, c.[CompetenciaNombre] AS Descripcion "
               "FROM [Competencias] c JOIN [CVIdiomas] i ON i.[CVIdiomaId] = c.[CompetenciaId]",
}

# --- Tablas de ejemplo (reemplazan a la base mientras no está conectada) ----
# Misma estructura que las tablas reales: Id -> descripción.
_EJEMPLO = {
    "CausalesBaja": {1: "Despido", 2: "Fin de contrato", 3: "Cierre de la empresa", 4: "Mudanza",
                     5: "Motivos personales", 6: "Estudios", 7: "Salud", 8: "Fin de zafra",
                     9: "Renuncia por mejor oferta", 12: "Otros"},
    "NivelesEducativos": {1: "Primaria", 2: "Ciclo básico", 3: "Bachillerato", 4: "Técnico / UTU",
                          5: "Terciario", 6: "Universitario", 7: "Posgrado"},
    "Departamentos": {1: "Montevideo", 2: "Canelones", 3: "Maldonado", 4: "San José", 5: "Colonia", 6: "Paysandú",
                      7: "Salto", 8: "Rivera", 9: "Soriano", 10: "Florida", 11: "Rocha", 12: "Tacuarembó",
                      13: "Cerro Largo", 14: "Durazno", 15: "Lavalleja", 16: "Artigas", 17: "Río Negro",
                      18: "Treinta y Tres", 19: "Flores"},
    "Localidades": {101: "Centro", 102: "Cordón", 103: "Pocitos", 104: "Malvín", 105: "Unión", 106: "Cerro",
                    107: "Colón", 108: "Piedras Blancas", 109: "La Teja", 110: "Buceo", 111: "Carrasco",
                    201: "Ciudad de la Costa", 202: "Las Piedras", 203: "Pando", 204: "La Paz", 205: "Progreso",
                    301: "Maldonado", 302: "Punta del Este", 303: "San Carlos", 304: "Piriápolis"},
    "EstadosCiviles": {1: "Soltero/a", 2: "Casado/a", 3: "Unión libre", 4: "Divorciado/a", 5: "Viudo/a"},
    "Idiomas": {501: "Inglés", 502: "Portugués", 503: "Italiano", 504: "Francés", 505: "Alemán"},
    "SectoresActividad": {1: "Comercio minorista", 2: "Industria manufacturera", 3: "Logística y transporte",
                          4: "Telecomunicaciones", 5: "Servicios financieros", 6: "Salud", 7: "Energía",
                          8: "Agro", 9: "Gastronomía y hotelería", 10: "Servicios profesionales",
                          11: "Construcción", 12: "Sector público"},
    "TiposCliente": {1: "Corporativo", 2: "PyME", 3: "Gobierno", 4: "Multinacional"},
    "EstadosCliente": {1: "Activo", 2: "Inactivo", 3: "Prospecto", 4: "Suspendido"},
    "Tendencias": {1: "Creciendo", 2: "Estable", 3: "Bajando"},
    "EjecutivosCuenta": {1: "A. Rodríguez", 2: "M. Fernández", 3: "L. Sosa", 4: "P. Martínez",
                         5: "C. Pereira", 6: "G. Silva", 7: "V. López", 8: "J. Romero"},
}
# Cursos y carreras de ejemplo: CursoId -> (CursoNombre, NivelEducativoId)
_EJEMPLO_CURSOS = {
    1: ("Primaria", 1), 2: ("Ciclo básico", 2), 3: ("Bachillerato diversificado", 3), 4: ("Bachillerato tecnológico", 3),
    5: ("Administración", 4), 6: ("Electricidad", 4), 7: ("Gastronomía", 4), 8: ("Informática", 4),
    9: ("Mecánica automotriz", 4), 10: ("Logística", 4), 11: ("Analista programador", 5), 12: ("Técnico en RRHH", 5),
    13: ("Marketing", 5), 14: ("Operador logístico", 5), 15: ("Contador público", 6), 16: ("Lic. en Administración", 6),
    17: ("Ingeniería en sistemas", 6), 18: ("Psicología", 6), 19: ("Lic. en Comunicación", 6), 20: ("Derecho", 6),
    21: ("Maestría en Administración", 7), 22: ("Posgrado en RRHH", 7),
}


def _leer(nombre):
    filas = consultar(CONSULTAS[nombre])
    return {int(f["Id"]): (f["Descripcion"] or "").strip() for f in filas}


def _crear_cargador(nombre):
    @cache_temporal()
    def cargar():
        return _leer(nombre) if sgo_configurada() else dict(_EJEMPLO[nombre])
    return cargar


_CARGADORES = {nombre: _crear_cargador(nombre) for nombre in CONSULTAS}


def catalogo(nombre):
    """{Id: descripción} de la tabla de referencia pedida."""
    return _CARGADORES[nombre]()


def descripcion(nombre, id_, defecto="Sin dato"):
    if id_ is None:
        return defecto
    return catalogo(nombre).get(int(id_), defecto)


@cache_temporal()
def cursos():
    """{CursoId: (CursoNombre, NivelEducativoId)}."""
    if not sgo_configurada():
        return dict(_EJEMPLO_CURSOS)
    filas = consultar("SELECT [CursoId], [CursoNombre], [NivelEducativoId] FROM [CursosCarreras]")
    return {int(f["CursoId"]): ((f["CursoNombre"] or "").strip(), int(f["NivelEducativoId"])) for f in filas}
