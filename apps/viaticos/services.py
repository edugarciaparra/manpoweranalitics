"""
Piezas comunes de las pantallas de Viáticos (migradas del SGO).

Los viáticos están en HistorialViaticos y se unen a la asignación por
(AsignacionId, PedidoId), como en el SGO.
"""
from apps.core import sgo
from apps.core.filtros import Filtro

F_CLIENTE = Filtro.uno("cliente_id", "Cliente", "ClientesConViaticos")
F_ANIO = Filtro.uno("anio", "Año", "AniosViaticos")
FILTROS_RESUMEN = [
    F_CLIENTE,
    Filtro.fecha("fecha_desde", "Desde"),
    Filtro.fecha("fecha_hasta", "Hasta"),
    Filtro.numero("importe_min", "Importe mínimo", None),
    Filtro.numero("importe_max", "Importe máximo", None),
]
FILTROS_ANIO = [F_CLIENTE, F_ANIO]

DESDE = """FROM dbo.HistorialViaticos hv
    INNER JOIN dbo.Asignaciones a ON hv.AsignacionId = a.AsignacionId AND hv.PedidoId = a.PedidoId
    INNER JOIN dbo.Pedidos p ON a.PedidoId = p.PedidoId"""
IMPORTE = "hv.HistorialViaticosImporte"
FECHA = "hv.HistorialViaticosFecha"
OBS = "RTRIM(ISNULL(hv.HistorialViaticosObs, ''))"
FECHA_VALIDA = f"{FECHA} IS NOT NULL AND {FECHA} > '1900-01-01'"


def where(filtros, con_anio=True):
    condiciones, params = ["1=1"], []
    if filtros.get("cliente_id") is not None:
        condiciones.append("p.ClienteId = %s")
        params.append(filtros["cliente_id"])
    if con_anio and filtros.get("anio") is not None:
        condiciones.append(f"YEAR({FECHA}) = %s")
        params.append(filtros["anio"])
    if filtros.get("fecha_desde"):
        condiciones.append(f"{FECHA} >= %s")
        params.append(filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        condiciones.append(f"{FECHA} <= %s")
        params.append(filtros["fecha_hasta"])
    if filtros.get("importe_min") is not None:
        condiciones.append(f"{IMPORTE} >= %s")
        params.append(filtros["importe_min"])
    if filtros.get("importe_max") is not None:
        condiciones.append(f"{IMPORTE} <= %s")
        params.append(filtros["importe_max"])
    return " AND ".join(condiciones), params


COLUMNAS_VIATICO = ["Viático", "Fecha", "Importe", "Observaciones", "Cliente", "Candidato", "Asignación", "Pedido"]


def viaticos(filtros, condicion="", params=None, orden=f"{FECHA} DESC", con_anio=True):
    """Hasta 500 viáticos con los filtros de la pantalla y una condición más."""
    w, p = where(filtros, con_anio)
    sql = f"""
        SELECT TOP 500 hv.ViaticoId, CONVERT(VARCHAR(10), {FECHA}, 103) AS fecha, {IMPORTE} AS importe,
               {OBS} AS observaciones, RTRIM(cl.ClienteNombre) AS cliente,
               RTRIM(cand.CandidatoNombre) + ' ' + RTRIM(cand.CandidatoApellido) AS candidato, hv.AsignacionId, hv.PedidoId
        {DESDE}
        INNER JOIN dbo.Clientes cl ON p.ClienteId = cl.ClienteId
        INNER JOIN dbo.Candidatos cand ON a.CandidatoId = cand.CandidatoId
        WHERE {w} {f'AND ({condicion})' if condicion else ''}
        ORDER BY {orden}"""
    return sgo.filas(sql, p + list(params or []))


def monto(v):
    return f"$ {sgo.num(v):,.0f}".replace(",", ".")


def monto_corto(v):
    n = sgo.num(v)
    if abs(n) >= 1_000_000:
        return f"$ {n / 1_000_000:.1f} M".replace(".", ",")
    if abs(n) >= 10_000:
        return f"$ {n / 1_000:.0f} mil"
    return monto(n)


# Categorías de gasto por palabras en la observación (mismas palabras que el SGO).
# Se buscan con CHARINDEX para no usar % en el SQL.
CATEGORIAS = {
    "Combustible": ["COMBUSTIBLE", "NAFTA", "GASOIL", "DIESEL"],
    "Peajes": ["PEAJE", "TOLL"],
    "Alimentación": ["COMIDA", "ALMUERZO", "CENA", "DESAYUNO", "VIANDA"],
    "Estacionamiento": ["ESTACIONAMIENTO", "PARKING"],
    "Alojamiento": ["HOTEL", "ALOJAMIENTO", "HOSPEDAJE"],
    "Taxi / transporte privado": ["TAXI", "UBER", "REMIS"],
    "Transporte público": ["COLECTIVO", "OMNIBUS", "BUS", "TREN", "SUBTE"],
    "Transporte aéreo": ["AVION", "VUELO"],
    "Mantenimiento / reparaciones": ["REPUESTO", "REPARACION", "MANTENIMIENTO"],
    "Herramientas / materiales": ["HERRAMIENTA", "MATERIAL"],
    "Comunicaciones": ["TELEFONO", "CELULAR", "INTERNET"],
}
PALABRAS_FRECUENTES = ["COMBUSTIBLE", "PEAJE", "COMIDA", "ESTACIONAMIENTO", "TAXI", "HOTEL", "ALMUERZO", "NAFTA", "VIAJE",
                       "TRASLADO", "CENA", "DESAYUNO", "PARKING", "UBER", "REMIS", "GASOIL", "DIESEL", "ALOJAMIENTO",
                       "VIANDA", "COLECTIVO"]


def contiene(palabra):
    return f"CHARINDEX('{palabra}', UPPER({OBS})) > 0"


def condicion_categoria(nombre):
    if nombre == "Otros":
        todas = " OR ".join(contiene(w) for ws in CATEGORIAS.values() for w in ws)
        return f"{OBS} != '' AND NOT ({todas})"
    palabras = CATEGORIAS.get(nombre)
    return "(" + " OR ".join(contiene(w) for w in palabras) + ")" if palabras else "1=0"


def resumen_landing():
    try:
        f = sgo.fila(f"""SELECT COUNT(*) AS cantidad, SUM({IMPORTE}) AS monto {DESDE}
                         WHERE YEAR({FECHA}) = YEAR(GETDATE()) AND MONTH({FECHA}) = MONTH(GETDATE())""")
    except Exception:  # noqa: BLE001
        return []
    return [{"valor": sgo.num(f.get("cantidad")), "texto": "viáticos este mes"},
            {"valor": monto_corto(f.get("monto")), "texto": "gastados este mes"}]
