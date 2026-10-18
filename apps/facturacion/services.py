"""
Piezas comunes de las pantallas de Órdenes de facturación (migradas del SGO).

Filtros del SGO: divisiones, estado del pedido, servicio, cliente, moneda y
rango de fechas sobre OrdenFecha. Valores como parámetros (%s).
"""
from datetime import date

from apps.core import sgo
from apps.core.filtros import Filtro

F_DIVISIONES = Filtro.varios("divisiones_ids", "Divisiones", "Divisiones")
F_ESTADO = Filtro.uno("estado_id", "Estado del pedido", "EstadosPedido")
F_SERVICIO = Filtro.uno("servicio_id", "Servicio", "Servicios")
F_CLIENTE = Filtro.uno("cliente_id", "Cliente", "ClientesConOrdenes")
F_MONEDA = Filtro.uno("moneda_id", "Moneda", "Monedas")
F_DESDE = Filtro.fecha("fecha_desde", "Desde")
F_HASTA = Filtro.fecha("fecha_hasta", "Hasta")

FILTROS = [F_DIVISIONES, F_ESTADO, F_SERVICIO, F_CLIENTE, F_MONEDA, F_DESDE, F_HASTA]
# El resumen del SGO arranca mostrando el año en curso
FILTROS_ANIO = [F_DIVISIONES, F_ESTADO, F_SERVICIO, F_CLIENTE, F_MONEDA,
                Filtro.fecha("fecha_desde", "Desde", defecto=lambda: date(date.today().year, 1, 1)),
                Filtro.fecha("fecha_hasta", "Hasta", defecto=lambda: date(date.today().year, 12, 31))]

DESDE = """FROM dbo.OrdenesFacturacion o
    INNER JOIN dbo.Pedidos p ON o.PedidoId = p.PedidoId
    INNER JOIN dbo.Divisiones d ON p.DivisionId = d.DivisionId"""


def where(filtros):
    condiciones, params = ["1=1"], []
    if filtros.get("divisiones_ids"):
        texto, valores = sgo.en_lista("p.DivisionId", filtros["divisiones_ids"])
        condiciones.append(texto)
        params += valores
    for clave, columna in (("estado_id", "p.EstadoPedidoId"), ("servicio_id", "o.OrdenServicioId"),
                           ("cliente_id", "p.ClienteId"), ("moneda_id", "o.OrdenMonCod")):
        if filtros.get(clave) is not None:
            condiciones.append(f"{columna} = %s")
            params.append(filtros[clave])
    if filtros.get("fecha_desde"):
        condiciones.append("o.OrdenFecha >= %s")
        params.append(filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        condiciones.append("o.OrdenFecha <= %s")
        params.append(filtros["fecha_hasta"])
    return " AND ".join(condiciones), params


def moneda_principal(filtros):
    """Símbolo de la moneda con más órdenes (los montos del SGO se suman sin convertir)."""
    if filtros.get("moneda_id") is not None:
        w, p = "m.moncod = %s", [filtros["moneda_id"]]
        r = sgo.valor(f"SELECT TOP 1 RTRIM(m.monsmb) AS monsmb FROM dbo.Monedas m WHERE {w}", p)
    else:
        w, p = where(filtros)
        r = sgo.valor(f"""SELECT TOP 1 RTRIM(m.monsmb) AS monsmb {DESDE}
            INNER JOIN dbo.Monedas m ON o.OrdenMonCod = m.moncod
            WHERE {w} GROUP BY m.monsmb ORDER BY COUNT(*) DESC""", p)
    return (str(r).strip() if r else "") or "$"


def monto(v, simbolo="$"):
    return f"{simbolo} {sgo.num(v):,.0f}".replace(",", ".")


def monto_corto(v, simbolo="$"):
    n = sgo.num(v)
    if abs(n) >= 1_000_000:
        return f"{simbolo} {n / 1_000_000:.1f} M".replace(".", ",")
    if abs(n) >= 1_000:
        return f"{simbolo} {n / 1_000:.0f} mil"
    return monto(n, simbolo)


COLUMNAS_ORDEN = ["Orden", "Cliente", "Servicio", "División", "Fecha", "Monto", "Moneda"]
SELECT_ORDEN = """
    SELECT TOP 500 o.OrdenId, c.ClienteNombre AS cliente, s.ServicioDescripcion AS servicio,
           d.DivisionDescripcion AS division, CONVERT(VARCHAR(10), o.OrdenFecha, 103) AS fecha,
           o.OrdenMonto AS monto, ISNULL(RTRIM(m.monsmb), '$') AS moneda
    FROM dbo.OrdenesFacturacion o
    INNER JOIN dbo.Pedidos p ON o.PedidoId = p.PedidoId
    INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
    INNER JOIN dbo.Servicios s ON o.OrdenServicioId = s.ServicioId
    INNER JOIN dbo.Divisiones d ON p.DivisionId = d.DivisionId
    LEFT JOIN dbo.Monedas m ON o.OrdenMonCod = m.moncod
    {joins}
    WHERE {where} {condicion}
    ORDER BY {orden}
"""


def ordenes(filtros, condicion="", params=None, joins="", orden="o.OrdenFecha DESC"):
    w, p = where(filtros)
    sql = SELECT_ORDEN.format(joins=joins, where=w, condicion=f"AND {condicion}" if condicion else "", orden=orden)
    return sgo.filas(sql, p + list(params or []))


def resumen_landing():
    try:
        f = sgo.fila(f"""
            SELECT COUNT(*) AS ordenes, COUNT(DISTINCT p.ClienteId) AS clientes
            {DESDE} WHERE o.OrdenFecha >= DATEFROMPARTS(YEAR(GETDATE()), 1, 1)""")
    except Exception:  # noqa: BLE001
        return []
    return [
        {"valor": sgo.num(f.get("ordenes")), "texto": "órdenes este año"},
        {"valor": sgo.num(f.get("clientes")), "texto": "clientes facturados"},
    ]
