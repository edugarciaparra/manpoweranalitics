"""
Tablas de referencia de sgo_new (Id -> descripción).

Las descripciones nunca se escriben en el código de los análisis: salen de estas
tablas, que se leen siempre de la base de Manpower.

    catalogo("CausalesBaja")        {CausalBajaId: CausalBajaDescripcion}
    catalogo("NivelesEducativos")   {NivelEducativoId: NivelEducativoDescripcion} (ordenado por Id)
    cursos()                        {CursoId: (CursoNombre, NivelEducativoId)}
"""
from .cache import cache_temporal
from .db import consultar

CONSULTAS = {
    "CausalesBaja": "SELECT [CausalBajaId] AS Id, [CausalBajaDescripcion] AS Descripcion FROM [CausalesBaja]",
    "NivelesEducativos": "SELECT [NivelEducativoId] AS Id, [NivelEducativoDescripcion] AS Descripcion "
                         "FROM [NivelesEducativos] ORDER BY [NivelEducativoId]",
    "Departamentos": "SELECT [DepartamentoId] AS Id, [DepartamentoNombre] AS Descripcion FROM [Departamentos]",
    "Localidades": "SELECT [LocalidadId] AS Id, [LocalidadNombre] AS Descripcion FROM [Localidades]",
    "EstadosCiviles": "SELECT [EstadoCivilId] AS Id, [EstadoCivilDescripcion] AS Descripcion FROM [EstadosCiviles]",
    # Clientes (columnas confirmadas con INFORMATION_SCHEMA el 18/10/2026)
    "SectoresActividad": "SELECT [SectorActividadId] AS Id, [SectorActividadDescripcion] AS Descripcion FROM [SectoresActividad]",
    "TiposCliente": "SELECT [TipoClienteId] AS Id, [TipoClienteDescripcion] AS Descripcion FROM [TiposCliente]",
    "EstadosCliente": "SELECT [EstadoClienteId] AS Id, [EstadoClienteDescripcion] AS Descripcion FROM [EstadosCliente]",
    "Tendencias": "SELECT [TendenciaId] AS Id, [TendenciaDescripcion] AS Descripcion FROM [Tendencias]",
    "EjecutivosCuenta": "SELECT [EjecutivoCuentaId] AS Id, "
                        "LTRIM(RTRIM(ISNULL([EjecutivoCuentaNombre], ''))) + ' ' + LTRIM(RTRIM(ISNULL([EjecutivoCuentaApellido], ''))) "
                        "AS Descripcion FROM [EjecutivosCuenta]",
    # Pedidos, asignaciones, entrevistas y facturación
    "Divisiones": "SELECT [DivisionId] AS Id, [DivisionDescripcion] AS Descripcion FROM [Divisiones]",
    "EstadosPedido": "SELECT [EstadoPedidoId] AS Id, [EstadoPedidoDescripcion] AS Descripcion FROM [EstadosPedido]",
    "TiposPedido": "SELECT [TipoPedidoId] AS Id, [TipoPedidoDescripcion] AS Descripcion FROM [TiposPedido]",
    "TiposAsignacion": "SELECT [TipoAsignacionId] AS Id, [TipoAsignacionDescripcion] AS Descripcion FROM [TiposAsignacion]",
    "EstadosAsignacion": "SELECT [EstadoAsignacionId] AS Id, [EstadoAsignacionDescripcion] AS Descripcion FROM [EstadosAsignacion]",
    "Psicologos": "SELECT [PsicologoId] AS Id, LTRIM(RTRIM(ISNULL([PsicologoNombre], ''))) + ' ' + "
                  "LTRIM(RTRIM(ISNULL([PsicologoApellido], ''))) AS Descripcion FROM [Psicologos]",
    "CanalesPublicacionAvisos": "SELECT [CanalPublicacionId] AS Id, [CanalPublicacionDescripcion] AS Descripcion "
                                "FROM [CanalesPublicacionAvisos]",
    "PerfilesCandidatos": "SELECT [PerfilCandidatoId] AS Id, [PerfilCandidatoDescripcion] AS Descripcion "
                          "FROM [PerfilesCandidatos]",
    "ClientesConViaticos": "SELECT DISTINCT c.[ClienteId] AS Id, c.[ClienteNombre] AS Descripcion FROM [Clientes] c "
                           "JOIN [Pedidos] p ON p.[ClienteId] = c.[ClienteId] "
                           "JOIN [HistorialViaticos] hv ON hv.[PedidoId] = p.[PedidoId]",
    "AniosViaticos": "SELECT DISTINCT YEAR([HistorialViaticosFecha]) AS Id, CAST(YEAR([HistorialViaticosFecha]) AS VARCHAR(4)) "
                     "AS Descripcion FROM [HistorialViaticos] WHERE [HistorialViaticosFecha] > '1900-01-01'",
    "ClientesAnalitica": "SELECT DISTINCT c.[ClienteId] AS Id, c.[ClienteNombre] AS Descripcion FROM [Clientes] c "
                         "JOIN [analitica_cliente_individual] a ON a.[ClienteId] = c.[ClienteId]",
    "AniosAnalitica": "SELECT DISTINCT [Anio] AS Id, CAST([Anio] AS VARCHAR(4)) AS Descripcion FROM [analitica_cliente_individual]",
    "ClientesConAsignaciones": "SELECT DISTINCT c.[ClienteId] AS Id, c.[ClienteNombre] AS Descripcion FROM [Clientes] c "
                               "JOIN [Pedidos] p ON p.[ClienteId] = c.[ClienteId] JOIN [Asignaciones] a ON a.[PedidoId] = p.[PedidoId]",
    "ClientesConEntrevistas": "SELECT DISTINCT c.[ClienteId] AS Id, c.[ClienteNombre] AS Descripcion FROM [Clientes] c "
                              "JOIN [Pedidos] p ON p.[ClienteId] = c.[ClienteId] JOIN [Entrevistas] e ON e.[EntrevistaPedidoId] = p.[PedidoId]",
    "AniosAsignaciones": "SELECT DISTINCT YEAR([AsignacionFechaIngreso]) AS Id, CAST(YEAR([AsignacionFechaIngreso]) AS VARCHAR(4)) "
                         "AS Descripcion FROM [Asignaciones] WHERE [AsignacionFechaIngreso] > '1900-01-01'",
    "Paises": "SELECT [PaisId] AS Id, [PaisNombre] AS Descripcion FROM [Paises]",
    "CategoriasLibretaConducir": "SELECT [CategoriaLibretaConducirId] AS Id, [CategoriaLibretaConducirDescri] AS Descripcion "
                                 "FROM [CategoriasLibretaConducir]",
    "Pruebas": "SELECT [PruebaId] AS Id, [PruebaDescripcion] AS Descripcion FROM [Pruebas]",
    "SituacionesLaborales": "SELECT [SituacionLaboralId] AS Id, [SituacionLaboralNombre] AS Descripcion "
                            "FROM [SituacionesLaborales]",
    "Servicios": "SELECT [ServicioId] AS Id, [ServicioDescripcion] AS Descripcion FROM [Servicios]",
    "Monedas": "SELECT [moncod] AS Id, LTRIM(RTRIM(ISNULL([mondsc], ''))) + ' (' + LTRIM(RTRIM(ISNULL([monsmb], ''))) + ')' "
               "AS Descripcion FROM [Monedas]",
    "ClientesConOrdenes": "SELECT DISTINCT c.[ClienteId] AS Id, c.[ClienteNombre] AS Descripcion FROM [Clientes] c "
                          "JOIN [Pedidos] p ON p.[ClienteId] = c.[ClienteId] "
                          "JOIN [OrdenesFacturacion] o ON o.[PedidoId] = p.[PedidoId]",
    # Solo las competencias que se usan como idioma en los CV
    "Idiomas": "SELECT DISTINCT c.[CompetenciaId] AS Id, c.[CompetenciaNombre] AS Descripcion "
               "FROM [Competencias] c JOIN [CVIdiomas] i ON i.[CVIdiomaId] = c.[CompetenciaId]",
}

def _leer(nombre):
    filas = consultar(CONSULTAS[nombre])
    return {int(f["Id"]): (f["Descripcion"] or "").strip() for f in filas}


def _crear_cargador(nombre):
    @cache_temporal()
    def cargar():
        return _leer(nombre)
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
    filas = consultar("SELECT [CursoId], [CursoNombre], [NivelEducativoId] FROM [CursosCarreras]")
    return {int(f["CursoId"]): ((f["CursoNombre"] or "").strip(), int(f["NivelEducativoId"])) for f in filas}
