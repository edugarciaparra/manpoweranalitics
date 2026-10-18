"""
Piezas comunes de las pantallas de Pedidos (migradas de apps/analitica del SGO).

Mismos filtros y criterios que el SGO: divisiones, estado, tipo de pedido,
tipo de asignación y rango de fechas sobre PedidoFecha. La diferencia es que
acá los valores van como parámetros (%s) y no pegados en el texto del SQL.
"""
from apps.core import sgo
from apps.core.filtros import Filtro

FILTROS = [
    Filtro.varios("divisiones_ids", "Divisiones", "Divisiones"),
    Filtro.uno("estado_id", "Estado", "EstadosPedido"),
    Filtro.uno("tipo_pedido_id", "Tipo de pedido", "TiposPedido"),
    Filtro.uno("tipo_asignacion_id", "Tipo de asignación", "TiposAsignacion"),
    Filtro.fecha("fecha_desde", "Desde"),
    Filtro.fecha("fecha_hasta", "Hasta"),
]

# Fechas de cierre "vacías": el SGO guarda 1900-01-01 o 1753-01-01 en vez de NULL
FECHAS_NULAS = "(CAST('1900-01-01' AS DATETIME), CAST('1753-01-01' AS DATETIME))"
SIN_CIERRE = f"(p.PedidoFechaCierre IS NULL OR p.PedidoFechaCierre IN {FECHAS_NULAS})"
CON_CIERRE = f"(p.PedidoFechaCierre IS NOT NULL AND p.PedidoFechaCierre NOT IN {FECHAS_NULAS})"
A_TIEMPO = "p.PedidoFechaEntregaEfectiva IS NOT NULL AND p.PedidoFechaEntregaEfectiva <= p.PedidoFechaTopeEntrega"
TARDE = "p.PedidoFechaEntregaEfectiva IS NOT NULL AND p.PedidoFechaEntregaEfectiva > p.PedidoFechaTopeEntrega"

# Estados por Id, como los usa el SGO
FINALIZADO = 9
CERRADOS_SLA = "(8, 9)"          # Cubierto y Finalizado
SLA_DETALLE = "(2, 5)"           # estados que usa el SGO en la pantalla de SLA
CANCELADOS = "(3, 6)"            # Cancelado y No cubierto
ACTIVOS = "(7, 2, 4, 8)"
ABIERTOS_ZOMBIE = "(7, 2, 4, 8, 5)"
CERRADOS_TIEMPO = "(8, 9, 3, 6)"

# Asignaciones válidas del SGO: asignaciones con ingreso que no están rechazadas,
# más los postulantes con evento de asignación (11, 12), sin duplicar pedido-candidato.
_EXTRAS_ASIGNACION = {
    "fechas": ("a.AsignacionFechaIngreso, a.AsignacionFechaEgreso",
               "pp.PostulanteFecha AS AsignacionFechaIngreso, NULL AS AsignacionFechaEgreso"),
    "estado": ("a.EstadoAsignacionId", "NULL AS EstadoAsignacionId"),
    "ejecutivo": ("a.AsignacionEjecutivoId", "NULL AS AsignacionEjecutivoId"),
}


def asignaciones_validas(extra=None):
    """Subconsulta (PedidoId, CandidatoId[, columnas extra]) para usar con JOIN ... asig."""
    col_a, col_pp = _EXTRAS_ASIGNACION[extra] if extra else ("", "")
    return f"""
        SELECT a.PedidoId, a.CandidatoId{', ' + col_a if col_a else ''}
        FROM dbo.Asignaciones a
        INNER JOIN dbo.EstadosAsignacion ea ON a.EstadoAsignacionId = ea.EstadoAsignacionId
        WHERE a.AsignacionFechaIngreso IS NOT NULL AND a.AsignacionFechaIngreso != ''
          AND ea.EstadoAsignacionDescripcion != 'Rechazado'
        UNION
        SELECT pp.PedidoId, pp.PostulanteCandidatoId AS CandidatoId{', ' + col_pp if col_pp else ''}
        FROM dbo.PedidosPostulante pp
        WHERE pp.EventoId IN (11, 12)
          AND pp.PostulanteFecha = (SELECT MAX(pp2.PostulanteFecha) FROM dbo.PedidosPostulante pp2
                                    WHERE pp2.PedidoId = pp.PedidoId
                                      AND pp2.PostulanteCandidatoId = pp.PostulanteCandidatoId)"""


def where(filtros, alias="p"):
    """(condición SQL, parámetros) con los filtros de la pantalla."""
    condiciones, params = ["1=1"], []
    if filtros.get("divisiones_ids"):
        texto, valores = sgo.en_lista(f"{alias}.DivisionId", filtros["divisiones_ids"])
        condiciones.append(texto)
        params += valores
    for clave, columna in (("estado_id", "EstadoPedidoId"), ("tipo_pedido_id", "TipoPedidoId"),
                           ("tipo_asignacion_id", "TipoAsignacionId")):
        if filtros.get(clave) is not None:
            condiciones.append(f"{alias}.{columna} = %s")
            params.append(filtros[clave])
    if filtros.get("fecha_desde"):
        condiciones.append(f"{alias}.PedidoFecha >= %s")
        params.append(filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        condiciones.append(f"{alias}.PedidoFecha <= %s")
        params.append(filtros["fecha_hasta"])
    return " AND ".join(condiciones), params


# --- Registros para los modales -------------------------------------------
COLUMNAS_PEDIDO = ["Número", "Cliente", "División", "Estado", "Fecha", "Vacantes"]
SELECT_PEDIDO = """
    SELECT TOP 500 p.PedidoNumero, c.ClienteNombre AS cliente, d.DivisionDescripcion AS division,
           e.EstadoPedidoDescripcion AS estado, CONVERT(VARCHAR(10), p.PedidoFecha, 103) AS fecha,
           p.PedidoCantidadPersonas AS vacantes{extra}
    FROM dbo.Pedidos p
    INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
    INNER JOIN dbo.Divisiones d ON p.DivisionId = d.DivisionId
    INNER JOIN dbo.EstadosPedido e ON p.EstadoPedidoId = e.EstadoPedidoId
    {joins}
    WHERE {where} {condicion}
    ORDER BY {orden}
"""
EXTRA_TOPE = """,
           CASE WHEN p.PedidoFechaTopeEntrega IS NOT NULL THEN CONVERT(VARCHAR(10), p.PedidoFechaTopeEntrega, 103)
                ELSE 'Sin tope' END AS tope,
           CASE WHEN p.PedidoFechaEntregaEfectiva IS NOT NULL THEN CONVERT(VARCHAR(10), p.PedidoFechaEntregaEfectiva, 103)
                ELSE 'Sin entrega' END AS entrega"""
EXTRA_DIFERENCIA = EXTRA_TOPE + """,
           DATEDIFF(DAY, p.PedidoFechaTopeEntrega, p.PedidoFechaEntregaEfectiva) AS dias_diferencia"""


def pedidos(filtros, condicion="", params=None, extra="", joins="", orden="p.PedidoFecha DESC"):
    """Hasta 500 pedidos con los filtros de la pantalla y una condición más."""
    w, p = where(filtros)
    sql = SELECT_PEDIDO.format(extra=extra, joins=joins, where=w,
                               condicion=f"AND {condicion}" if condicion else "", orden=orden)
    return sgo.filas(sql, p + list(params or []))


def columnas_pedido(extra=()):
    return COLUMNAS_PEDIDO + list(extra)


def resumen_landing():
    """Dos indicadores para la tarjeta del módulo en la portada."""
    try:
        f = sgo.fila(f"""
            SELECT COUNT(CASE WHEN {SIN_CIERRE} THEN 1 END) AS abiertos,
                   COUNT(CASE WHEN {SIN_CIERRE} AND p.PedidoFechaEntregaEfectiva IS NULL
                                   AND DATEDIFF(DAY, p.PedidoFecha, GETDATE()) > 30
                                   AND p.EstadoPedidoId IN {ABIERTOS_ZOMBIE} THEN 1 END) AS zombie
            FROM dbo.Pedidos p""")
    except Exception:  # noqa: BLE001
        return []
    return [
        {"valor": sgo.num(f.get("abiertos")), "texto": "abiertos"},
        {"valor": sgo.num(f.get("zombie")), "texto": "sin movimiento +30 días", "alerta": True},
    ]
