"""
Datos del módulo Clientes (tabla [Clientes]).

Con la base conectada, clientes() lee CONSULTA_SGO: sector, tipo, estado,
tendencia y ejecutivos salen de sus tablas con JOIN, y la actividad de cada
cliente (último pedido, pedidos y facturación de los últimos 12 meses y de los
12 anteriores) se calcula en SQL Server a partir de [Pedidos] y
[OrdenesFacturacion].

Sin conexión se generan clientes de ejemplo que guardan los Id y buscan las
descripciones en las tablas de referencia (apps/core/catalogos.py).
"""
import random
from datetime import date, timedelta

from apps.core.cache import cache_temporal
from apps.core.catalogos import catalogo
from apps.core.db import consultar, sgo_configurada

# Códigos reales (consulta del 18/10/2026)
SI = "S"                 # ClienteOpera... y ClienteUtilizaPersonalTemporal: S / N
ESTADO_ACTIVO_ID = 2     # EstadoClienteId del estado activo en la tabla EstadosCliente
# ClienteRanking y ClienteEstado están vacíos en todos los clientes: no se usan.

# Actividad de cada cliente según su último pedido (se muestra en el modal)
ACTIVIDADES = ["Pidió en los últimos 90 días", "Más de 90 días sin pedir", "Nunca pidió"]

# Líneas de servicio: etiqueta -> campo del registro
LINEAS = {
    "Administrativa": "opera_adm",
    "Industrial": "opera_ind",
    "Profesional": "opera_pro",
    "Promociones": "opera_promo",
    "RPO": "opera_rpo",
}
# Rol del ejecutivo -> columna de [Clientes]
ROLES_EJECUTIVO = {
    "RPO": "ClienteRpoEjecutivoId",
    "Promociones": "ClientePrmEjecutivoId",
    "Profesional": "ClienteProEjecutivoId",
    "Industrial": "ClienteIndEjecutivoId",
    "Administrativa": "ClienteAdmEjecutivoId",
}

CONSULTA_SGO = """
SELECT c.[ClienteId], c.[ClienteNombre], c.[ClienteRazonSocial], c.[ClienteRUT],
       c.[SectorActividadId], sa.[SectorActividadDescripcion], tc.[TipoClienteDescripcion],
       c.[EstadoClienteId], ec.[EstadoClienteDescripcion], t.[TendenciaDescripcion],
       c.[ClienteRanking], c.[ClienteFechaIngreso], c.[ClienteComprasAnuales], c.[ClienteFacturacionAnual],
       c.[ClienteCantidadAsociadosManpow], c.[ClienteCantidadAsociadosTotal],
       c.[ClienteOperaAdministrativa], c.[ClienteOperaIndustrial], c.[ClienteOperaProfesional],
       c.[ClienteOperaPromociones], c.[ClienteOperaRPO], c.[ClienteUtilizaPersonalTemporal],
       LTRIM(RTRIM(ISNULL(eRpo.[EjecutivoCuentaNombre], ''))) + ' ' + LTRIM(RTRIM(ISNULL(eRpo.[EjecutivoCuentaApellido], ''))) AS EjecRPO,
       LTRIM(RTRIM(ISNULL(ePrm.[EjecutivoCuentaNombre], ''))) + ' ' + LTRIM(RTRIM(ISNULL(ePrm.[EjecutivoCuentaApellido], ''))) AS EjecPromociones,
       LTRIM(RTRIM(ISNULL(ePro.[EjecutivoCuentaNombre], ''))) + ' ' + LTRIM(RTRIM(ISNULL(ePro.[EjecutivoCuentaApellido], ''))) AS EjecProfesional,
       LTRIM(RTRIM(ISNULL(eInd.[EjecutivoCuentaNombre], ''))) + ' ' + LTRIM(RTRIM(ISNULL(eInd.[EjecutivoCuentaApellido], ''))) AS EjecIndustrial,
       LTRIM(RTRIM(ISNULL(eAdm.[EjecutivoCuentaNombre], ''))) + ' ' + LTRIM(RTRIM(ISNULL(eAdm.[EjecutivoCuentaApellido], ''))) AS EjecAdministrativa,
       p.[UltimoPedido], ISNULL(p.[Pedidos12m], 0) AS Pedidos12m, ISNULL(p.[PedidosPrev], 0) AS PedidosPrev,
       ISNULL(f.[Facturado12m], 0) AS Facturado12m, ISNULL(f.[FacturadoPrev], 0) AS FacturadoPrev
FROM [Clientes] c
LEFT JOIN [SectoresActividad] sa ON sa.[SectorActividadId] = c.[SectorActividadId]
LEFT JOIN [TiposCliente] tc ON tc.[TipoClienteId] = c.[TipoClienteId]
LEFT JOIN [EstadosCliente] ec ON ec.[EstadoClienteId] = c.[EstadoClienteId]
LEFT JOIN [Tendencias] t ON t.[TendenciaId] = c.[TendenciaId]
LEFT JOIN [EjecutivosCuenta] eRpo ON eRpo.[EjecutivoCuentaId] = c.[ClienteRpoEjecutivoId]
LEFT JOIN [EjecutivosCuenta] ePrm ON ePrm.[EjecutivoCuentaId] = c.[ClientePrmEjecutivoId]
LEFT JOIN [EjecutivosCuenta] ePro ON ePro.[EjecutivoCuentaId] = c.[ClienteProEjecutivoId]
LEFT JOIN [EjecutivosCuenta] eInd ON eInd.[EjecutivoCuentaId] = c.[ClienteIndEjecutivoId]
LEFT JOIN [EjecutivosCuenta] eAdm ON eAdm.[EjecutivoCuentaId] = c.[ClienteAdmEjecutivoId]
LEFT JOIN (
    SELECT [ClienteId], MAX([PedidoFecha]) AS UltimoPedido,
           SUM(CASE WHEN [PedidoFecha] >= DATEADD(month, -12, GETDATE()) THEN 1 ELSE 0 END) AS Pedidos12m,
           SUM(CASE WHEN [PedidoFecha] >= DATEADD(month, -24, GETDATE())
                     AND [PedidoFecha] < DATEADD(month, -12, GETDATE()) THEN 1 ELSE 0 END) AS PedidosPrev
    FROM [Pedidos] GROUP BY [ClienteId]
) p ON p.[ClienteId] = c.[ClienteId]
LEFT JOIN (
    SELECT pe.[ClienteId],
           SUM(CASE WHEN o.[OrdenFecha] >= DATEADD(month, -12, GETDATE()) THEN o.[OrdenMonto] ELSE 0 END) AS Facturado12m,
           SUM(CASE WHEN o.[OrdenFecha] >= DATEADD(month, -24, GETDATE())
                     AND o.[OrdenFecha] < DATEADD(month, -12, GETDATE()) THEN o.[OrdenMonto] ELSE 0 END) AS FacturadoPrev
    FROM [OrdenesFacturacion] o JOIN [Pedidos] pe ON pe.[PedidoId] = o.[PedidoId]
    GROUP BY pe.[ClienteId]
) f ON f.[ClienteId] = c.[ClienteId]
"""


def _texto(v):
    return (v or "").strip() if isinstance(v, str) else v


def _fecha(v):
    return v.date() if hasattr(v, "date") else v


def _completar(fila):
    """Campos calculados a partir de los datos base."""
    hoy = date.today()
    ingreso = fila["fecha_ingreso"]
    fila["antiguedad"] = round((hoy - ingreso).days / 365.25, 1) if ingreso else 0
    up = fila["ultimo_pedido"]
    fila["dias_sin_pedir"] = (hoy - up).days if up else None
    total, mp = fila["asociados_total"], fila["asociados_mp"]
    fila["penetracion"] = round(mp / total * 100, 1) if total else 0
    fila["lineas"] = [nombre for nombre, campo in LINEAS.items() if fila[campo]]
    return fila


def _desde_sgo():
    filas = []
    for r in consultar(CONSULTA_SGO):
        ejecutivos = {rol: _texto(r[f"Ejec{rol}"]) for rol in ROLES_EJECUTIVO if _texto(r[f"Ejec{rol}"])}
        filas.append(_completar({
            "id": int(r["ClienteId"]), "nombre": _texto(r["ClienteNombre"]),
            "razon_social": _texto(r["ClienteRazonSocial"]), "rut": int(r["ClienteRUT"] or 0),
            "sector": _texto(r["SectorActividadDescripcion"]) or "Sin dato",
            "tipo": _texto(r["TipoClienteDescripcion"]) or "Sin dato",
            "estado_id": int(r["EstadoClienteId"]), "estado": _texto(r["EstadoClienteDescripcion"]) or "Sin dato",
            "tendencia": _texto(r["TendenciaDescripcion"]) or "Sin dato",
            "fecha_ingreso": _fecha(r["ClienteFechaIngreso"]),
            "compras_anuales": float(r["ClienteComprasAnuales"] or 0),
            "facturacion_cliente": float(r["ClienteFacturacionAnual"] or 0),
            "asociados_mp": int(r["ClienteCantidadAsociadosManpow"] or 0),
            "asociados_total": int(r["ClienteCantidadAsociadosTotal"] or 0),
            "opera_adm": _texto(r["ClienteOperaAdministrativa"]) == SI,
            "opera_ind": _texto(r["ClienteOperaIndustrial"]) == SI,
            "opera_pro": _texto(r["ClienteOperaProfesional"]) == SI,
            "opera_promo": _texto(r["ClienteOperaPromociones"]) == SI,
            "opera_rpo": _texto(r["ClienteOperaRPO"]) == SI,
            "usa_temporal": _texto(r["ClienteUtilizaPersonalTemporal"]) == SI,
            "ejecutivos": ejecutivos,
            "ultimo_pedido": _fecha(r["UltimoPedido"]),
            "pedidos_12m": int(r["Pedidos12m"]), "pedidos_prev": int(r["PedidosPrev"]),
            "facturado_12m": float(r["Facturado12m"]), "facturado_prev": float(r["FacturadoPrev"]),
        }))
    return tuple(filas)


# --- Datos de ejemplo -------------------------------------------------------
_PREFIJOS = ["Grupo", "Comercial", "Industrias", "Servicios", "Distribuidora", "Logística", "Laboratorios",
             "Hoteles", "Agro", "Tecno", "Constructora", "Farmacias", "Transportes", "Alimentos"]
_SUFIJOS = ["del Sur", "Oriental", "Andina", "Rioplatense", "Atlántica", "Central", "del Norte", "del Plata",
            "Uruguaya", "Integral", "del Este", "Costera", "Unida", "Moderna", "Federal"]


def _ejemplo():
    r = random.Random(77)
    hoy = date.today()
    sectores, tipos = catalogo("SectoresActividad"), catalogo("TiposCliente")
    estados, tendencias = catalogo("EstadosCliente"), catalogo("Tendencias")
    ejecutivos = catalogo("EjecutivosCuenta")
    ids_sector, ids_tipo, ids_estado = sorted(sectores), sorted(tipos), sorted(estados)
    ids_tend, ids_ejec = sorted(tendencias), sorted(ejecutivos)

    filas, usados = [], set()
    for i in range(420):
        nombre = f"{r.choice(_PREFIJOS)} {r.choice(_SUFIJOS)}"
        if nombre in usados:  # hay menos combinaciones que clientes: se numeran las repetidas
            n = 2
            while f"{nombre} {n}" in usados:
                n += 1
            nombre = f"{nombre} {n}"
        usados.add(nombre)
        # Distribución de estados parecida a una cartera real: mayoría activos, después inactivos y potenciales
        peso_estado = {ESTADO_ACTIVO_ID: 55, 4: 15, 6: 10, 5: 7, 3: 4, 7: 3, 8: 3, 9: 2, 1: 1}
        estado_id = r.choices(ids_estado, weights=[peso_estado.get(x, 1) for x in ids_estado])[0]
        activo = estado_id == ESTADO_ACTIVO_ID
        tamano = r.choices([6, 2.5, 1], weights=[18, 37, 45])[0]
        total = max(5, int(r.lognormvariate(4.2, 1.0) * tamano))
        mp = min(total, int(total * r.betavariate(1.3, 6))) if activo or r.random() < .3 else 0
        ingreso = hoy - timedelta(days=int(r.random() ** .8 * 365 * 22))

        # Actividad: los activos piden más; algunos están "dormidos"
        if activo:
            dias = int(r.expovariate(1 / 45)) if r.random() > .18 else r.randint(120, 400)
        else:
            dias = r.randint(200, 1500) if r.random() > .15 else None
        base_pedidos = max(0, int(r.gauss(tamano * 3, tamano)))
        p12 = base_pedidos if activo and dias is not None and dias < 365 else 0
        prev = max(0, int(base_pedidos * r.uniform(.6, 1.4))) if dias is not None else 0
        ticket = r.uniform(25000, 60000)

        lineas = {campo: r.random() < pr for campo, pr in zip(LINEAS.values(), [.55, .38, .22, .18, .08])}
        if not any(lineas.values()):
            lineas["opera_adm"] = True
        roles = [rol for rol, campo in zip(ROLES_EJECUTIVO, ["opera_rpo", "opera_promo", "opera_pro", "opera_ind", "opera_adm"])
                 if lineas[campo]]
        ejecutivo_principal = r.choice(ids_ejec)
        filas.append(_completar({
            "id": 2000 + i, "nombre": nombre, "razon_social": f"{nombre} S.A.",
            "rut": r.randint(210000000000, 219999999999),
            # Descripciones por Id desde las tablas de referencia (como el JOIN de la consulta real)
            "sector": sectores[r.choice(ids_sector)], "tipo": tipos[r.choices(ids_tipo, weights=[30, 52, 8, 10][:len(ids_tipo)])[0]],
            "estado_id": estado_id, "estado": estados[estado_id],
            "tendencia": tendencias[r.choices(ids_tend, weights=[28, 47, 25][:len(ids_tend)])[0]],
            "fecha_ingreso": ingreso,
            "compras_anuales": round(total * r.uniform(8000, 22000), -3),
            "facturacion_cliente": round(total * r.uniform(1.5e6, 4e6), -4),
            "asociados_mp": mp, "asociados_total": total,
            **lineas, "usa_temporal": activo and r.random() < .8,
            "ejecutivos": {rol: ejecutivos[ejecutivo_principal if r.random() < .7 else r.choice(ids_ejec)] for rol in roles},
            "ultimo_pedido": hoy - timedelta(days=dias) if dias is not None else None,
            "pedidos_12m": p12, "pedidos_prev": prev,
            "facturado_12m": round(p12 * ticket, -3), "facturado_prev": round(prev * ticket * r.uniform(.85, 1.1), -3),
        }))
    return tuple(filas)


@cache_temporal()
def clientes():
    return _desde_sgo() if sgo_configurada() else _ejemplo()


def estado_activo():
    """Descripción del estado activo, leída de la tabla EstadosCliente."""
    return catalogo("EstadosCliente").get(ESTADO_ACTIVO_ID, "Activo")


def es_activo(c):
    return c["estado_id"] == ESTADO_ACTIVO_ID


def activos():
    return [c for c in clientes() if es_activo(c)]


def actividad(c):
    dias = c["dias_sin_pedir"]
    if dias is None:
        return ACTIVIDADES[2]
    return ACTIVIDADES[0] if dias <= 90 else ACTIVIDADES[1]


# Columnas del modal de detalle
COLUMNAS_DETALLE = ["Id", "Cliente", "RUT", "Sector", "Tipo", "Estado", "Actividad", "Último pedido",
                    "Pedidos 12m", "Facturado 12m", "Asociados Manpower"]


def fila_detalle(c):
    from apps.core.utils import formato_numero, formato_pesos
    return [
        c["id"], c["nombre"], c["rut"] or "—", c["sector"], c["tipo"], c["estado"], actividad(c),
        c["ultimo_pedido"].strftime("%d/%m/%Y") if c["ultimo_pedido"] else "Nunca",
        c["pedidos_12m"], formato_pesos(c["facturado_12m"]) if c["facturado_12m"] else "—",
        f"{formato_numero(c['asociados_mp'])} de {formato_numero(c['asociados_total'])}",
    ]


def resumen_landing():
    act = activos()
    return [
        {"valor": len(act), "texto": "activos"},
        {"valor": sum(1 for c in act if c["dias_sin_pedir"] is None or c["dias_sin_pedir"] > 90),
         "texto": "sin pedidos en 90 días", "alerta": True},
    ]
