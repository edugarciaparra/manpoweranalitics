"""
Pantallas de clientes migradas de la analítica del SGO: resumen de clientes,
segmentación, estacionalidad, insights de un cliente, KPI de asignaciones y
pedidos con sus asignaciones.

Usan las tablas resumen que ya tiene sgo_new para el SGO
(analitica_clientes_totales, analitica_clientessegmentacion y
analitica_cliente_individual) y las tablas de pedidos y asignaciones.
"""
import math
from collections import defaultdict

from apps.core import graficos as g
from apps.core import sgo
from apps.core.analisis import seccion
from apps.core.filtros import Filtro
from apps.core.pantalla import (
    decimal, detalle as respuesta_detalle, entero, etiquetas, extremos, kpi, lider, pct, proporcion, tabla, total,
    valores,
)
from apps.core.sgo import num

from .analisis import catalogo

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


# ==========================================================================
# 1. Resumen de clientes (ana_cli): analitica_clientes_totales
# ==========================================================================
FILTROS_RESUMEN = [
    Filtro.uno("sector", "Sector", "SectoresActividad"),
    Filtro.uno("tipo_cliente", "Tipo de cliente", "TiposCliente"),
    Filtro.uno("estado", "Estado", "EstadosCliente"),
    Filtro.uno("tendencia", "Tendencia", "Tendencias"),
]


def _where_totales(filtros):
    condiciones, params = ["1=1"], []
    for clave, columna in (("sector", "SectorActividadId"), ("tipo_cliente", "TipoClienteId"),
                           ("estado", "EstadoClienteId"), ("tendencia", "TendenciaId")):
        if filtros.get(clave) is not None:
            condiciones.append(f"act.{columna} = %s")
            params.append(filtros[clave])
    return " AND ".join(condiciones), params


@catalogo.registrar(
    "resumen-sgo", "Resumen de clientes (SGO)",
    "Clientes, asociados y operaciones por sector, tipo, estado y tendencia, penetración de Manpower y mix de líneas.",
    usa_periodo=False, icono="bi-pie-chart", filtros=FILTROS_RESUMEN,
)
def resumen_sgo(periodo, filtros):
    w, p = _where_totales(filtros)
    desde = "FROM analitica_clientes_totales act"
    k = sgo.fila(f"""
        SELECT ISNULL(SUM(act.TotalClientes), 0) AS total_clientes, ISNULL(SUM(act.CantAsociadosManpow), 0) AS total_asociados_manpow,
               ISNULL(SUM(act.CantAsociadosTotal), 0) AS total_asociados_total,
               ISNULL(SUM(act.CantOperaAdmin + act.CantOperaIndustrial + act.CantOperaProfesional + act.CantOperaPromociones), 0) AS total_operaciones,
               CASE WHEN SUM(act.CantAsociadosTotal) > 0 THEN ROUND(CAST(SUM(act.CantAsociadosManpow) AS FLOAT) / SUM(act.CantAsociadosTotal) * 100, 2) ELSE 0 END AS penetracion_manpower,
               CASE WHEN SUM(act.TotalClientes) > 0 THEN ROUND(CAST(SUM(act.CantAsociadosTotal) AS FLOAT) / SUM(act.TotalClientes), 2) ELSE 0 END AS avg_asociados_cliente
        {desde} WHERE {w}""", p)

    def por(join_tabla, id_col, desc_col):
        return sgo.filas(f"""
            SELECT x.{desc_col} AS label, SUM(act.TotalClientes) AS value
            {desde} LEFT JOIN {join_tabla} x ON act.{id_col} = x.{id_col}
            WHERE {w} GROUP BY x.{desc_col} ORDER BY value DESC""", p)

    sectores = por("SectoresActividad", "SectorActividadId", "SectorActividadDescripcion")
    tipos = por("TiposCliente", "TipoClienteId", "TipoClienteDescripcion")
    estados = por("EstadosCliente", "EstadoClienteId", "EstadoClienteDescripcion")
    tendencias = por("Tendencias", "TendenciaId", "TendenciaDescripcion")
    mix = sgo.fila(f"""
        SELECT ISNULL(SUM(act.CantOperaAdmin), 0) AS admin, ISNULL(SUM(act.CantOperaIndustrial), 0) AS industrial,
               ISNULL(SUM(act.CantOperaProfesional), 0) AS profesional, ISNULL(SUM(act.CantOperaPromociones), 0) AS promociones
        {desde} WHERE {w}""", p)
    penetracion = sgo.filas(f"""
        SELECT sa.SectorActividadDescripcion AS label,
               CASE WHEN SUM(act.CantAsociadosTotal) > 0 THEN ROUND(CAST(SUM(act.CantAsociadosManpow) AS FLOAT) / SUM(act.CantAsociadosTotal) * 100, 2) ELSE 0 END AS value,
               CASE WHEN SUM(act.TotalClientes) > 0 THEN ROUND(CAST(SUM(act.CantAsociadosTotal) AS FLOAT) / SUM(act.TotalClientes), 2) ELSE 0 END AS eficiencia
        {desde} LEFT JOIN SectoresActividad sa ON act.SectorActividadId = sa.SectorActividadId
        WHERE {w} GROUP BY sa.SectorActividadDescripcion ORDER BY value DESC""", p)
    combinaciones = sgo.filas(f"""
        SELECT TOP 15 sa.SectorActividadDescripcion + ' / ' + tc.TipoClienteDescripcion AS label, SUM(act.TotalClientes) AS value
        {desde} LEFT JOIN SectoresActividad sa ON act.SectorActividadId = sa.SectorActividadId
        LEFT JOIN TiposCliente tc ON act.TipoClienteId = tc.TipoClienteId
        WHERE {w} GROUP BY sa.SectorActividadDescripcion, tc.TipoClienteDescripcion ORDER BY value DESC""", p)

    pares_mix = [("Administrativa", num(mix.get("admin"))), ("Industrial", num(mix.get("industrial"))),
                 ("Profesional", num(mix.get("profesional"))), ("Promociones", num(mix.get("promociones")))]
    pares_mix.sort(key=lambda x: -x[1])
    eficiencia = sorted(penetracion, key=lambda r: -num(r["eficiencia"]))

    def bloque(titulo, filas, explicacion, color=None):
        return seccion(titulo, [lider(filas, "label", "value", "clientes")],
                       g.ranking(etiquetas(filas), valores(filas, "value"), "Clientes", color),
                       alto=g.alto_ranking(len(filas), 200), explicacion=explicacion)

    secciones = [
        bloque("Clientes por sector", sectores, "Clientes por sector de actividad (tabla resumen analitica_clientes_totales)."),
        bloque("Clientes por tipo", tipos, "Clientes por tipo de cliente.", g.SERIES[1]),
        bloque("Clientes por estado", estados, "Clientes por estado comercial.", g.SERIES[2]),
        bloque("Clientes por tendencia", tendencias, "Clientes según su tendencia.", g.SERIES[3]),
        seccion(
            "Mix de operaciones",
            [f"La línea con más operaciones es {pares_mix[0][0]}." if pares_mix and pares_mix[0][1] else ""],
            g.columnas([e for e, _ in pares_mix], {"Operaciones": [v for _, v in pares_mix]}, rotar=0),
            explicacion="Cantidad de operaciones de cada línea: administrativa, industrial, profesional y promociones.",
        ),
        seccion(
            "Penetración de Manpower por sector",
            [extremos(penetracion, "label", "value", pct, "mayor penetración", "menor")],
            g.ranking(etiquetas(penetracion), valores(penetracion, "value"), "% de penetración", formato="fmt:pct"),
            alto=g.alto_ranking(len(penetracion)),
            explicacion="Asociados de Manpower ÷ asociados totales de los clientes del sector × 100.",
        ),
        seccion(
            "Eficiencia: asociados por cliente",
            [extremos(eficiencia, "label", "eficiencia", decimal, "más asociados por cliente", "menos")],
            g.ranking(etiquetas(eficiencia), valores(eficiencia, "eficiencia"), "Asociados por cliente", g.SERIES[2]),
            alto=g.alto_ranking(len(eficiencia)),
            explicacion="Asociados totales ÷ clientes, por sector.",
        ),
        seccion(
            "Top 15 combinaciones sector / tipo",
            [lider(combinaciones, "label", "value", "clientes", "el top 15")],
            g.ranking(etiquetas(combinaciones), valores(combinaciones, "value"), "Clientes", g.SERIES[1]),
            alto=g.alto_ranking(len(combinaciones)),
            explicacion="Combinaciones de sector y tipo de cliente con más clientes.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total clientes", entero(k.get("total_clientes"))),
            kpi("Total asociados", entero(k.get("total_asociados_total")), f"{entero(k.get('total_asociados_manpow'))} de Manpower"),
            kpi("Total operaciones", entero(k.get("total_operaciones"))),
            kpi("Penetración Manpower", pct(k.get("penetracion_manpower")), "",
                "Asociados de Manpower ÷ asociados totales de los clientes × 100."),
            kpi("Asociados por cliente", decimal(k.get("avg_asociados_cliente")), "promedio"),
        ],
        "conclusiones": [
            f"{entero(k.get('total_clientes'))} clientes con {entero(k.get('total_asociados_total'))} asociados; "
            f"Manpower tiene el {pct(k.get('penetracion_manpower'))}.",
            lider(sectores, "label", "value", "clientes"),
            extremos(penetracion, "label", "value", pct, "sector de mayor penetración", "menor"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿En qué sectores tenemos menos penetración?", "¿Qué línea de operación es la más grande?"],
        "contexto_ia": {"kpis": k, "sectores": sectores, "tipos": tipos, "estados": estados, "penetracion": penetracion},
    }


# ==========================================================================
# 2. Segmentación de clientes (ana_cli_seg): analitica_clientessegmentacion
# ==========================================================================
SEGMENTOS = ["VIP", "Activo", "Riesgo", "Inactivo"]
DESCRIPCION_SEGMENTO = {
    "VIP": "Pedido hace menos de 60 días y 20 personas o más: clientes estratégicos.",
    "Activo": "Pedido hace menos de 90 días con volumen medio.",
    "Riesgo": "Entre 90 y 180 días sin pedidos: actividad en descenso.",
    "Inactivo": "Más de 180 días sin pedidos.",
}


@catalogo.registrar(
    "segmentacion", "Segmentación (VIP, activo, riesgo, inactivo)",
    "Clientes según recencia y volumen de pedidos, con los días que llevan sin pedir.",
    usa_periodo=False, icono="bi-bullseye",
    filtros=[Filtro.uno("segmento", "Segmento", opciones={s: s for s in SEGMENTOS})],
)
def segmentacion(periodo, filtros):
    conteo = sgo.filas("""
        SELECT a.SegmentoCliente AS label, COUNT(*) AS value, SUM(a.CantidadPedidos) AS pedidos,
               SUM(a.TotalPersonasSolicitadas) AS personas, AVG(CAST(a.DiasSinPedido AS FLOAT)) AS dias_promedio
        FROM analitica_clientessegmentacion a GROUP BY a.SegmentoCliente""")
    conteo = sorted(conteo, key=lambda r: SEGMENTOS.index(r["label"]) if r["label"] in SEGMENTOS else 9)
    w, p = ("a.SegmentoCliente = %s", [filtros["segmento"]]) if filtros.get("segmento") else ("1=1", [])
    clientes = sgo.filas(f"""
        SELECT TOP 500 c.ClienteRazonSocial AS cliente, a.SegmentoCliente AS segmento, a.CantidadPedidos AS pedidos,
               a.TotalPersonasSolicitadas AS personas, a.DiasSinPedido AS dias, CONVERT(VARCHAR(10), a.UltimaFechaPedido, 103) AS ultima
        FROM analitica_clientessegmentacion a INNER JOIN Clientes c ON c.ClienteId = a.ClienteId
        WHERE {w} ORDER BY a.DiasSinPedido DESC""", p)
    por = {r["label"]: num(r["value"]) for r in conteo}
    total_c = sum(por.values())
    colores = {"VIP": g.SERIES[0], "Activo": g.SERIES[2], "Riesgo": g.SERIES[3], "Inactivo": g.NEUTRO}
    grafico = g.columnas(etiquetas(conteo), {"Clientes": valores(conteo, "value")}, rotar=0)
    grafico["series"][0]["data"] = [{"value": num(r["value"]), "itemStyle": {"color": colores.get(r["label"], g.SERIES[0])}}
                                    for r in conteo]
    secciones = [
        seccion(
            "Clientes por segmento",
            [f"{entero(por.get('Riesgo', 0))} clientes están en riesgo (90 a 180 días sin pedir)."],
            grafico,
            explicacion=" ".join(f"{s}: {d}" for s, d in DESCRIPCION_SEGMENTO.items()),
            detalle="segmento", ayuda_detalle="Hacé clic en un segmento para ver sus clientes.",
            tabla=tabla("Segmentos", ["Segmento", "Clientes", "Pedidos", "Personas pedidas", "Días sin pedir (promedio)"],
                        [[r["label"], entero(r["value"]), entero(r["pedidos"]), entero(r["personas"]), decimal(r["dias_promedio"])]
                         for r in conteo]),
        ),
        seccion(
            f"Clientes {('del segmento ' + filtros['segmento']) if filtros.get('segmento') else '(todos)'}",
            ["Ordenados por días sin pedir, de mayor a menor."],
            tabla=tabla("Clientes", ["Cliente", "Segmento", "Pedidos", "Personas", "Días sin pedido", "Último pedido"],
                        [[r["cliente"], r["segmento"], entero(r["pedidos"]), entero(r["personas"]), entero(r["dias"]), r["ultima"]]
                         for r in clientes[:200]]),
            explicacion="Elegí un segmento en los filtros para ver solo esos clientes.",
        ),
    ]
    return {
        "kpis": [kpi("Total clientes", entero(total_c))] + [
            kpi(s if s != "Riesgo" else "En riesgo", entero(por.get(s, 0)), pct(proporcion(por.get(s, 0), total_c)),
                DESCRIPCION_SEGMENTO[s], alerta=s == "Riesgo" and por.get(s, 0) > 0) for s in SEGMENTOS],
        "conclusiones": [
            f"De {entero(total_c)} clientes, {entero(por.get('VIP', 0))} son VIP y {entero(por.get('Activo', 0))} activos.",
            f"{entero(por.get('Riesgo', 0))} clientes están en riesgo y {entero(por.get('Inactivo', 0))} inactivos.",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué clientes en riesgo pedían más personas?", "¿Cuántos clientes VIP tenemos?"],
        "contexto_ia": {"segmentos": conteo},
    }


@catalogo.detalle("segmentacion")
def detalle_segmentacion(clave, valor, serie, periodo, filtros):
    filas = sgo.filas("""
        SELECT TOP 500 c.ClienteRazonSocial AS cliente, a.CantidadPedidos AS pedidos, a.TotalPersonasSolicitadas AS personas,
               a.DiasSinPedido AS dias, CONVERT(VARCHAR(10), a.UltimaFechaPedido, 103) AS ultima
        FROM analitica_clientessegmentacion a INNER JOIN Clientes c ON c.ClienteId = a.ClienteId
        WHERE a.SegmentoCliente = %s ORDER BY a.DiasSinPedido DESC""", [valor])
    return respuesta_detalle(f"Clientes · {valor}", ["Cliente", "Pedidos", "Personas", "Días sin pedido", "Último pedido"], filas)


# ==========================================================================
# 3. Estacionalidad (ana_estacionalidad): analitica_cliente_individual
# ==========================================================================
F_ANIO_DESDE = Filtro.uno("anio_inicio", "Desde el año", "AniosAnalitica")
F_ANIO_HASTA = Filtro.uno("anio_fin", "Hasta el año", "AniosAnalitica")


def _where_anios(filtros, alias=""):
    a = f"{alias}." if alias else ""
    condiciones, params = [], []
    if filtros.get("anio_inicio") is not None:
        condiciones.append(f"{a}Anio >= %s")
        params.append(filtros["anio_inicio"])
    if filtros.get("anio_fin") is not None:
        condiciones.append(f"{a}Anio <= %s")
        params.append(filtros["anio_fin"])
    return condiciones, params


@catalogo.registrar(
    "estacionalidad", "Estacionalidad de pedidos",
    "Qué meses y trimestres concentran los pedidos: mapa año × mes, índice de estacionalidad y su variabilidad.",
    usa_periodo=False, icono="bi-thermometer-sun",
    filtros=[F_ANIO_DESDE, F_ANIO_HASTA, Filtro.uno("tipo_pedido_id", "Tipo de pedido", "TiposPedido")],
)
def estacionalidad(periodo, filtros):
    condiciones, params = _where_anios(filtros)
    if filtros.get("tipo_pedido_id") is not None:
        condiciones.append("TipoPedidoId = %s")
        params.append(filtros["tipo_pedido_id"])
    filas = sgo.filas(f"""SELECT Anio AS anio, Mes AS mes, SUM(CantidadPedidos) AS pedidos FROM analitica_cliente_individual
                          WHERE {' AND '.join(condiciones) or '1=1'} GROUP BY Anio, Mes ORDER BY Anio, Mes""", params)
    datos = []
    for r in filas:
        try:
            datos.append({"anio": int(num(r["anio"], None)), "mes": int(num(r["mes"], None)), "pedidos": num(r["pedidos"])})
        except (TypeError, ValueError):
            continue
    datos = [d for d in datos if 1 <= d["mes"] <= 12]
    anios = sorted({d["anio"] for d in datos})[-10:]
    celdas = [[d["mes"] - 1, anios.index(d["anio"]), d["pedidos"]] for d in datos if d["anio"] in anios]

    por_mes = defaultdict(list)
    for d in datos:
        por_mes[d["mes"]].append(d["pedidos"])
    todos = [d["pedidos"] for d in datos]
    promedio_global = sum(todos) / len(todos) if todos else 1
    promedio = [sum(por_mes.get(m, [0])) / len(por_mes.get(m, [0])) for m in range(1, 13)]
    indice = [round(x / promedio_global * 100, 1) if promedio_global else 0 for x in promedio]
    desvio = []
    for m in range(1, 13):
        v = por_mes.get(m, [0])
        media = sum(v) / len(v)
        desvio.append(round(math.sqrt(sum((x - media) ** 2 for x in v) / len(v)), 1))
    total_p = sum(todos)
    trim = defaultdict(float)
    trim_anio = defaultdict(lambda: [None] * 4)
    for d in datos:
        t = (d["mes"] - 1) // 3
        trim[t + 1] += d["pedidos"]
        trim_anio[str(d["anio"])][t] = (trim_anio[str(d["anio"])][t] or 0) + d["pedidos"]
    proporcion_t = [round(proporcion(trim[t], total_p), 1) for t in range(1, 5)]
    alto = max(range(12), key=lambda i: indice[i]) if datos else 0
    bajo = min(range(12), key=lambda i: indice[i]) if datos else 0

    secciones = [
        seccion(
            "Evolución mensual (mapa año × mes)",
            ["Las celdas más oscuras son los meses con más pedidos de cada año."],
            g.mapa_calor(MESES, [str(a) for a in anios], celdas), alto=max(300, 34 * len(anios) + 120),
            explicacion="Pedidos de cada mes (columnas) en cada año (filas), hasta 10 años.",
        ),
        seccion(
            "Promedio mensual e índice de estacionalidad",
            [f"{MESES[alto]} es el mes más fuerte (índice {decimal(indice[alto])}) y {MESES[bajo]} el más flojo "
             f"(índice {decimal(indice[bajo])})." if datos else ""],
            g.columnas(MESES, {"Índice de estacionalidad": indice}, rotar=0),
            explicacion="Índice = promedio de pedidos del mes ÷ promedio de todos los meses × 100. Más de 100 es un "
                        "mes por encima de lo normal.",
            tabla=tabla("Por mes", ["Mes", "Promedio de pedidos", "Índice", "Desvío entre años"],
                        [[MESES[i], decimal(promedio[i]), decimal(indice[i]), decimal(desvio[i])] for i in range(12)]),
        ),
        seccion(
            "Proporción de pedidos por trimestre",
            [f"El trimestre más fuerte es el T{proporcion_t.index(max(proporcion_t)) + 1} con el "
             f"{pct(max(proporcion_t))} de los pedidos." if total_p else ""],
            g.columnas(["T1", "T2", "T3", "T4"], {"% de los pedidos": proporcion_t}, formato="fmt:pct", rotar=0,
                       colores=[g.SERIES[2]]),
            explicacion="Qué parte de los pedidos de todos los años cae en cada trimestre.",
        ),
        seccion(
            "Evolución trimestral",
            [],
            g.columnas(["T1", "T2", "T3", "T4"], {a: trim_anio[a] for a in sorted(trim_anio)[-4:]}, rotar=0),
            explicacion="Pedidos por trimestre; cada color es un año (los 4 más recientes).",
        ),
    ]
    return {
        "kpis": [
            kpi("Pedidos analizados", entero(total_p)),
            kpi("Mes más fuerte", MESES[alto] if datos else "—", f"índice {decimal(indice[alto])}" if datos else ""),
            kpi("Mes más flojo", MESES[bajo] if datos else "—", f"índice {decimal(indice[bajo])}" if datos else ""),
            kpi("Años", entero(len(anios))),
        ],
        "conclusiones": [
            f"{MESES[alto]} tiene un {pct(indice[alto] - 100)} más de pedidos que un mes promedio." if datos else "",
            f"{MESES[bajo]} es el mes de menor demanda." if datos else "",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué meses conviene reforzar el equipo de selección?", "¿La estacionalidad cambió en los últimos años?"],
        "contexto_ia": {"indice": dict(zip(MESES, indice)), "proporcion_trimestral": proporcion_t},
    }


# ==========================================================================
# 4. Insights de un cliente (ana_cli_det): analitica_cliente_individual
# ==========================================================================
F_CLIENTE = Filtro.uno("cliente_id", "Cliente", "ClientesAnalitica")


def _cliente_elegido(filtros, tabla_base="analitica_cliente_individual"):
    """El cliente del filtro o, si no eligió ninguno, el de más pedidos."""
    if filtros.get("cliente_id") is not None:
        return filtros["cliente_id"], False
    if tabla_base == "analitica_cliente_individual":
        r = sgo.valor("SELECT TOP 1 ClienteId FROM analitica_cliente_individual GROUP BY ClienteId ORDER BY SUM(CantidadPedidos) DESC")
    else:
        r = sgo.valor("SELECT TOP 1 ClienteId FROM Pedidos GROUP BY ClienteId ORDER BY COUNT(*) DESC")
    return (int(num(r)) if r is not None else None), True


def _nombre_cliente(cliente_id):
    from apps.core.catalogos import catalogo as tabla_ref
    try:
        nombre = tabla_ref("ClientesAnalitica").get(int(cliente_id))
    except Exception:  # noqa: BLE001
        nombre = None
    return nombre or str(sgo.valor("SELECT ClienteNombre FROM Clientes WHERE ClienteId = %s", [cliente_id]) or cliente_id)


@catalogo.registrar(
    "insights-cliente", "Insights de un cliente",
    "Todo sobre un cliente: pedidos, personas, horas, cancelaciones, evolución, estados, tipos, divisiones y practice areas.",
    usa_periodo=False, icono="bi-person-vcard", filtros=[F_CLIENTE, F_ANIO_DESDE, F_ANIO_HASTA],
)
def insights_cliente(periodo, filtros):
    cliente_id, por_defecto = _cliente_elegido(filtros)
    if cliente_id is None:
        return {"kpis": [], "conclusiones": [], "secciones": [seccion("Sin datos", ["No hay clientes en la tabla resumen."])]}
    nombre = _nombre_cliente(cliente_id)
    condiciones, extra = _where_anios(filtros, "a")
    w = " AND ".join(["a.ClienteId = %s"] + condiciones)
    p = [cliente_id] + extra
    k = sgo.fila(f"""
        SELECT COUNT(DISTINCT CAST(a.Anio AS VARCHAR) + '-' + CAST(a.Mes AS VARCHAR)) AS meses_activos,
               SUM(a.CantidadPedidos) AS total_pedidos, SUM(a.CantidadPersonas) AS total_personas,
               SUM(a.HorasMensualesTotales) AS total_horas, SUM(a.VacantesCanceladas) AS total_canceladas,
               AVG(a.HorasMensualesPromedio) AS promedio_horas, AVG(a.DiasPromedioCierre) AS promedio_dias_cierre
        FROM analitica_cliente_individual a WHERE {w}""", p)
    evolucion = sgo.filas(f"""SELECT a.Anio AS anio, a.Mes AS mes, SUM(a.CantidadPedidos) AS pedidos, SUM(a.CantidadPersonas) AS personas
                              FROM analitica_cliente_individual a WHERE {w} GROUP BY a.Anio, a.Mes ORDER BY a.Anio, a.Mes""", p)
    anual = sgo.filas(f"""SELECT a.Anio AS anio, SUM(a.CantidadPedidos) AS pedidos, SUM(a.CantidadPersonas) AS personas,
                                 SUM(a.HorasMensualesTotales) AS horas, SUM(a.VacantesCanceladas) AS canceladas, AVG(a.DiasPromedioCierre) AS dias_cierre
                          FROM analitica_cliente_individual a WHERE {w} GROUP BY a.Anio ORDER BY a.Anio""", p)

    def por(join, id_col, desc, top=""):
        return sgo.filas(f"""
            SELECT {top} RTRIM(x.{desc}) AS label, SUM(a.CantidadPedidos) AS pedidos, SUM(a.CantidadPersonas) AS personas
            FROM analitica_cliente_individual a INNER JOIN {join} x ON a.{id_col} = x.{id_col}
            WHERE {w} GROUP BY x.{desc} ORDER BY SUM(a.CantidadPedidos) DESC""", p)

    estados = por("EstadosPedido", "EstadoPedidoId", "EstadoPedidoDescripcion")
    tipos = por("TiposPedido", "TipoPedidoId", "TipoPedidoDescripcion")
    divisiones = por("Divisiones", "DivisionId", "DivisionDescripcion", "TOP 10")
    practice = por("PracticeAreas", "PracticeAreaId", "PracticeAreaDescripcion")
    trimestral = sgo.filas(f"""
        SELECT a.Anio AS anio, CASE WHEN a.Mes <= 3 THEN 1 WHEN a.Mes <= 6 THEN 2 WHEN a.Mes <= 9 THEN 3 ELSE 4 END AS trimestre,
               SUM(a.CantidadPedidos) AS pedidos
        FROM analitica_cliente_individual a WHERE {w}
        GROUP BY a.Anio, CASE WHEN a.Mes <= 3 THEN 1 WHEN a.Mes <= 6 THEN 2 WHEN a.Mes <= 9 THEN 3 ELSE 4 END
        ORDER BY a.Anio, trimestre""", p)

    def ym(r):
        try:
            return f"{int(num(r['anio'], None))}-{int(num(r['mes'], None)):02d}"
        except (TypeError, ValueError):
            return str(r.get("mes"))

    anios = [str(int(num(r["anio"]))) for r in anual]
    crecimiento = [0.0] + [round(proporcion(num(anual[i]["pedidos"]) - num(anual[i - 1]["pedidos"]), anual[i - 1]["pedidos"]), 1)
                           for i in range(1, len(anual))]
    total_ped, canceladas = num(k.get("total_pedidos")), num(k.get("total_canceladas"))
    aviso = [f"Se muestra {nombre}, el cliente con más pedidos. Elegí otro en Filtros."] if por_defecto else []
    secciones = [
        seccion(
            f"Evolución mensual de pedidos · {nombre}",
            aviso,
            g.lineas([ym(r) for r in evolucion], {"Pedidos": valores(evolucion, "pedidos"), "Personas": valores(evolucion, "personas")}),
            explicacion="Pedidos y personas pedidas por mes, de la tabla resumen analitica_cliente_individual.",
        ),
        seccion(
            "Comparativa anual",
            [],
            g.columnas(anios, {"Pedidos": valores(anual, "pedidos"), "Personas": valores(anual, "personas")}, rotar=0),
            explicacion="Pedidos y personas por año.",
            tabla=tabla("Por año", ["Año", "Pedidos", "Personas", "Horas", "Canceladas", "Días de cierre"],
                        [[a, entero(r["pedidos"]), entero(r["personas"]), entero(r["horas"]), entero(r["canceladas"]),
                          decimal(r["dias_cierre"])] for a, r in zip(anios, anual)]),
        ),
        seccion(
            "Crecimiento anual de pedidos",
            [],
            g.columnas(anios, {"Crecimiento": crecimiento}, formato="fmt:pct", rotar=0),
            explicacion="Variación de los pedidos de cada año contra el anterior.",
        ),
        seccion("Distribución por estado", [lider(estados, "label", "pedidos", "pedidos")],
                g.torta([(r["label"], num(r["pedidos"])) for r in estados]) if len(estados) <= 6 else
                g.ranking(etiquetas(estados), valores(estados, "pedidos"), "Pedidos"),
                explicacion="Pedidos del cliente por estado.", detalle="estado",
                ayuda_detalle="Hacé clic en un estado para ver esos pedidos."),
        seccion("Mix de tipos de pedido", [lider(tipos, "label", "pedidos", "pedidos")],
                g.ranking(etiquetas(tipos), valores(tipos, "pedidos"), "Pedidos", g.SERIES[1]), alto=g.alto_ranking(len(tipos), 200),
                explicacion="Pedidos del cliente por tipo.", detalle="tipo",
                ayuda_detalle="Hacé clic en un tipo para ver esos pedidos."),
        seccion("Top divisiones", [lider(divisiones, "label", "pedidos", "pedidos")],
                g.ranking(etiquetas(divisiones), valores(divisiones, "pedidos"), "Pedidos", g.SERIES[2]),
                alto=g.alto_ranking(len(divisiones), 200), explicacion="Divisiones que atienden al cliente.", detalle="division",
                ayuda_detalle="Hacé clic en una división para ver esos pedidos."),
        seccion("Practice areas", [lider(practice, "label", "pedidos", "pedidos")],
                g.ranking(etiquetas(practice), valores(practice, "pedidos"), "Pedidos", g.SERIES[3]),
                alto=g.alto_ranking(len(practice), 200), explicacion="Pedidos por practice area."),
        seccion("Pedidos por trimestre", [],
                g.columnas([f"{int(num(r['anio']))}-T{int(num(r['trimestre']))}" for r in trimestral],
                           {"Pedidos": valores(trimestral, "pedidos")}),
                explicacion="Pedidos de cada trimestre."),
    ]
    return {
        "kpis": [
            kpi("Meses activos", entero(k.get("meses_activos"))),
            kpi("Total pedidos", entero(total_ped)),
            kpi("Total personas", entero(k.get("total_personas")),
                f"{decimal(proporcion(k.get('total_personas'), total_ped) / 100, 2)} por pedido"),
            kpi("Horas totales", entero(k.get("total_horas")), f"{decimal(k.get('promedio_horas'))} por mes"),
            kpi("Cancelación", pct(proporcion(canceladas, total_ped)), f"{entero(canceladas)} vacantes canceladas",
                alerta=proporcion(canceladas, total_ped) > 20),
            kpi("Días promedio de cierre", decimal(k.get("promedio_dias_cierre"))),
        ],
        "conclusiones": [
            f"{nombre}: {entero(total_ped)} pedidos y {entero(k.get('total_personas'))} personas en "
            f"{entero(k.get('meses_activos'))} meses activos.",
            lider(divisiones, "label", "pedidos", "pedidos"),
            f"Cancelación de {pct(proporcion(canceladas, total_ped))}.",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Cómo viene este cliente respecto del año pasado?", "¿Qué divisiones lo atienden?"],
        "contexto_ia": {"cliente": nombre, "kpis": k, "anual": anual, "estados": estados, "divisiones": divisiones},
    }


@catalogo.detalle("insights-cliente")
def detalle_insights(clave, valor, serie, periodo, filtros):
    cliente_id, _ = _cliente_elegido(filtros)
    condicion = {"estado": "RTRIM(e.EstadoPedidoDescripcion) = %s", "tipo": "RTRIM(tp.TipoPedidoDescripcion) = %s",
                 "division": "RTRIM(d.DivisionDescripcion) = %s"}.get(clave, "1=0")
    extra = []
    condiciones = ["p.ClienteId = %s", condicion]
    if filtros.get("anio_inicio") is not None:
        condiciones.append("YEAR(p.PedidoFecha) >= %s")
        extra.append(filtros["anio_inicio"])
    if filtros.get("anio_fin") is not None:
        condiciones.append("YEAR(p.PedidoFecha) <= %s")
        extra.append(filtros["anio_fin"])
    filas = sgo.filas(f"""
        SELECT TOP 500 p.PedidoNumero, d.DivisionDescripcion AS division, e.EstadoPedidoDescripcion AS estado,
               tp.TipoPedidoDescripcion AS tipo, CONVERT(VARCHAR(10), p.PedidoFecha, 103) AS fecha, p.PedidoCantidadPersonas AS vacantes
        FROM Pedidos p INNER JOIN Divisiones d ON d.DivisionId = p.DivisionId
        INNER JOIN EstadosPedido e ON e.EstadoPedidoId = p.EstadoPedidoId
        LEFT JOIN TiposPedido tp ON tp.TipoPedidoId = p.TipoPedidoId
        WHERE {' AND '.join(condiciones)} ORDER BY p.PedidoFecha DESC""", [cliente_id, valor] + extra)
    return respuesta_detalle(f"Pedidos · {valor}", ["Número", "División", "Estado", "Tipo", "Fecha", "Vacantes"], filas)


# ==========================================================================
# 5. KPI de asignaciones de un cliente (ana_asi_kpi)
# ==========================================================================
F_CLIENTE_PEDIDOS = Filtro.uno("cliente_id", "Cliente", "ClientesAnalitica")
FILTROS_ASIG = [F_CLIENTE_PEDIDOS, F_ANIO_DESDE, F_ANIO_HASTA, Filtro.uno("tipo_pedido_id", "Tipo de pedido", "TiposPedido"),
                Filtro.uno("division_id", "División", "Divisiones"), Filtro.uno("estado_pedido_id", "Estado del pedido", "EstadosPedido")]


def _where_asig(filtros, cliente_id):
    condiciones, params = ["P.ClienteId = %s"], [cliente_id]
    for clave, sql in (("anio_inicio", "YEAR(P.PedidoFecha) >= %s"), ("anio_fin", "YEAR(P.PedidoFecha) <= %s"),
                       ("tipo_pedido_id", "P.TipoPedidoId = %s"), ("division_id", "P.DivisionId = %s"),
                       ("estado_pedido_id", "P.EstadoPedidoId = %s")):
        if filtros.get(clave) is not None:
            condiciones.append(sql)
            params.append(filtros[clave])
    return " AND ".join(condiciones), params


ASIG_POR_PEDIDO = "LEFT JOIN (SELECT PedidoId, COUNT(*) AS AsignacionesPorPedido FROM dbo.Asignaciones GROUP BY PedidoId) A ON P.PedidoId = A.PedidoId"


@catalogo.registrar(
    "asignaciones-cliente", "KPI de asignaciones de un cliente",
    "Cobertura de los pedidos de un cliente: sin asignar, parciales y completos, bajas, estados y ejecutivos.",
    usa_periodo=False, icono="bi-person-check", filtros=FILTROS_ASIG,
)
def asignaciones_cliente(periodo, filtros):
    cliente_id, por_defecto = _cliente_elegido(filtros, "Pedidos")
    if cliente_id is None:
        return {"kpis": [], "conclusiones": [], "secciones": [seccion("Sin datos", ["No hay pedidos."])]}
    nombre = _nombre_cliente(cliente_id)
    w, p = _where_asig(filtros, cliente_id)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_pedidos, SUM(CASE WHEN asignaciones_realizadas = 0 THEN 1 ELSE 0 END) AS pedidos_sin_asignaciones,
               SUM(CASE WHEN asignaciones_realizadas > 0 AND asignaciones_realizadas < candidatos_solicitados THEN 1 ELSE 0 END) AS pedidos_parciales,
               SUM(CASE WHEN asignaciones_realizadas >= candidatos_solicitados AND candidatos_solicitados > 0 THEN 1 ELSE 0 END) AS pedidos_completos,
               SUM(candidatos_solicitados) AS total_candidatos, SUM(asignaciones_realizadas) AS total_asignaciones,
               CASE WHEN SUM(candidatos_solicitados) > 0 THEN SUM(asignaciones_realizadas) * 100.0 / SUM(candidatos_solicitados) ELSE 0 END AS pct_cobertura
        FROM (SELECT P.PedidoId, P.PedidoCantidadPersonas AS candidatos_solicitados, ISNULL(A.AsignacionesPorPedido, 0) AS asignaciones_realizadas
              FROM dbo.Pedidos P {ASIG_POR_PEDIDO} WHERE {w}) x""", p)
    bajas = sgo.filas(f"""
        SELECT c.CausalBajaDescripcion AS label, COUNT(*) AS total_asignaciones,
               SUM(CASE WHEN A.AsignacionFechaEgreso IS NOT NULL THEN 1 ELSE 0 END) AS egresos
        FROM dbo.Asignaciones A INNER JOIN dbo.Pedidos P ON A.PedidoId = P.PedidoId
        INNER JOIN dbo.CausalesBaja c ON c.CausalBajaId = A.CausalBajaId
        WHERE {w} AND A.CausalBajaId IS NOT NULL GROUP BY c.CausalBajaDescripcion ORDER BY total_asignaciones DESC""", p)
    tipos = sgo.filas(f"""SELECT tp.TipoPedidoDescripcion AS label, COUNT(*) AS total FROM dbo.Pedidos P
                          LEFT JOIN dbo.TiposPedido tp ON tp.TipoPedidoId = P.TipoPedidoId WHERE {w}
                          GROUP BY tp.TipoPedidoDescripcion ORDER BY total DESC""", p)
    divisiones = sgo.filas(f"""SELECT d.DivisionDescripcion AS label, COUNT(*) AS total FROM dbo.Pedidos P
                               LEFT JOIN dbo.Divisiones d ON d.DivisionId = P.DivisionId WHERE {w}
                               GROUP BY d.DivisionDescripcion ORDER BY total DESC""", p)
    calificaciones = sgo.filas(f"""SELECT cal.CalificacionDescripcion AS label, COUNT(*) AS total FROM dbo.Pedidos P
                                   LEFT JOIN dbo.CalificacionesProfesionales cal ON cal.CalificacionId = P.CalificacionId WHERE {w}
                                   GROUP BY cal.CalificacionDescripcion ORDER BY total DESC""", p)
    evolucion = sgo.filas(f"""
        SELECT YEAR(P.PedidoFecha) AS anio, MONTH(P.PedidoFecha) AS mes, SUM(P.PedidoCantidadPersonas) AS personas_pedidas,
               SUM(ISNULL(A.AsignacionesPorPedido, 0)) AS asignadas
        FROM dbo.Pedidos P {ASIG_POR_PEDIDO} WHERE {w} GROUP BY YEAR(P.PedidoFecha), MONTH(P.PedidoFecha) ORDER BY anio, mes""", p)
    estados = sgo.filas(f"""
        SELECT RTRIM(EA.EstadoAsignacionDescripcion) AS label, COUNT(*) AS total
        FROM dbo.Asignaciones A INNER JOIN dbo.Pedidos P ON A.PedidoId = P.PedidoId
        INNER JOIN dbo.EstadosAsignacion EA ON A.EstadoAsignacionId = EA.EstadoAsignacionId
        WHERE {w} GROUP BY EA.EstadoAsignacionDescripcion ORDER BY total DESC""", p)
    ejecutivos = sgo.filas(f"""
        SELECT COALESCE(E.EjecutivoCuentaNombreAbreviado, RTRIM(E.EjecutivoCuentaNombre) + ' ' + RTRIM(E.EjecutivoCuentaApellido), 'Sin ejecutivo') AS label,
               COUNT(*) AS total
        FROM dbo.Asignaciones A INNER JOIN dbo.Pedidos P ON A.PedidoId = P.PedidoId
        LEFT JOIN dbo.EjecutivosCuenta E ON A.AsignacionEjecutivoId = E.EjecutivoCuentaId
        WHERE {w} GROUP BY E.EjecutivoCuentaNombreAbreviado, E.EjecutivoCuentaNombre, E.EjecutivoCuentaApellido ORDER BY total DESC""", p)

    def ym(r):
        try:
            return f"{int(num(r['anio'], None))}-{int(num(r['mes'], None)):02d}"
        except (TypeError, ValueError):
            return str(r.get("mes"))

    cobertura = [("Sin asignaciones", num(k.get("pedidos_sin_asignaciones"))), ("Parciales", num(k.get("pedidos_parciales"))),
                 ("Completos", num(k.get("pedidos_completos")))]
    aviso = [f"Se muestra {nombre}, el cliente con más pedidos. Elegí otro en Filtros."] if por_defecto else []
    secciones = [
        seccion(
            f"Cobertura de los pedidos · {nombre}",
            aviso + [f"{pct(proporcion(cobertura[2][1], k.get('total_pedidos')))} de los pedidos está completo."],
            g.torta(cobertura, colores=[g.NEGATIVO, g.ESTADO["atencion"], g.POSITIVO]),
            explicacion="Sin asignaciones: el pedido no tiene ninguna. Parcial: tiene menos asignaciones que personas "
                        "pedidas. Completo: igual o más.",
            detalle="cobertura", ayuda_detalle="Hacé clic en una porción para ver esos pedidos.",
        ),
        seccion(
            "Evolución mensual: personas pedidas vs. asignadas",
            [],
            g.lineas([ym(r) for r in evolucion], {"Personas pedidas": valores(evolucion, "personas_pedidas"),
                                                  "Asignadas": valores(evolucion, "asignadas")}),
            explicacion="Por mes del pedido: personas pedidas y asignaciones registradas para esos pedidos.",
        ),
        seccion("Pedidos por tipo", [], g.ranking(etiquetas(tipos), valores(tipos, "total"), "Pedidos"),
                alto=g.alto_ranking(len(tipos), 180), explicacion="Pedidos del cliente por tipo."),
        seccion("Pedidos por división", [], g.ranking(etiquetas(divisiones), valores(divisiones, "total"), "Pedidos", g.SERIES[1]),
                alto=g.alto_ranking(len(divisiones), 180), explicacion="Pedidos del cliente por división."),
        seccion("Pedidos por calificación", [], g.ranking(etiquetas(calificaciones), valores(calificaciones, "total"), "Pedidos",
                                                          g.SERIES[2]),
                alto=g.alto_ranking(len(calificaciones), 180), explicacion="Calificación profesional pedida."),
        seccion("Bajas por causal", [lider(bajas, "label", "total_asignaciones", "bajas")],
                g.ranking(etiquetas(bajas), valores(bajas, "total_asignaciones"), "Asignaciones", g.NEGATIVO),
                alto=g.alto_ranking(len(bajas), 180), explicacion="Asignaciones con causal de baja registrada.", detalle="baja",
                ayuda_detalle="Hacé clic en una causal para ver esas asignaciones."),
        seccion("Asignaciones por estado", [lider(estados, "label", "total", "asignaciones")],
                g.ranking(etiquetas(estados), valores(estados, "total"), "Asignaciones", g.SERIES[3]),
                alto=g.alto_ranking(len(estados), 180), explicacion="Estado de las asignaciones del cliente.", detalle="estado",
                ayuda_detalle="Hacé clic en un estado para ver esas asignaciones."),
        seccion("Asignaciones por ejecutivo de cuenta", [lider(ejecutivos, "label", "total", "asignaciones")],
                g.ranking(etiquetas(ejecutivos), valores(ejecutivos, "total"), "Asignaciones", g.SERIES[4]),
                alto=g.alto_ranking(len(ejecutivos), 180), explicacion="Ejecutivo que registró cada asignación."),
    ]
    return {
        "kpis": [
            kpi("Total pedidos", entero(k.get("total_pedidos"))),
            kpi("Sin asignaciones", entero(k.get("pedidos_sin_asignaciones")), "", alerta=num(k.get("pedidos_sin_asignaciones")) > 0),
            kpi("Parciales", entero(k.get("pedidos_parciales"))),
            kpi("Completos", entero(k.get("pedidos_completos"))),
            kpi("Personas pedidas", entero(k.get("total_candidatos"))),
            kpi("Asignaciones", entero(k.get("total_asignaciones"))),
            kpi("Cobertura", pct(k.get("pct_cobertura")), "", "Asignaciones ÷ personas pedidas × 100."),
        ],
        "conclusiones": [
            f"{nombre}: cobertura de {pct(k.get('pct_cobertura'))} ({entero(k.get('total_asignaciones'))} asignaciones para "
            f"{entero(k.get('total_candidatos'))} personas pedidas).",
            f"{entero(k.get('pedidos_sin_asignaciones'))} pedidos no tienen ninguna asignación.",
            lider(bajas, "label", "total_asignaciones", "bajas"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Por qué se dan de baja las asignaciones de este cliente?", "¿Cuántos pedidos quedaron sin cubrir?"],
        "contexto_ia": {"cliente": nombre, "kpis": k, "bajas": bajas, "estados": estados},
    }


@catalogo.detalle("asignaciones-cliente")
def detalle_asignaciones(clave, valor, serie, periodo, filtros):
    cliente_id, _ = _cliente_elegido(filtros, "Pedidos")
    w, p = _where_asig(filtros, cliente_id)
    if clave == "cobertura":
        condicion = {"Sin asignaciones": "ISNULL(A.AsignacionesPorPedido, 0) = 0",
                     "Parciales": "ISNULL(A.AsignacionesPorPedido, 0) > 0 AND ISNULL(A.AsignacionesPorPedido, 0) < P.PedidoCantidadPersonas",
                     "Completos": "ISNULL(A.AsignacionesPorPedido, 0) >= P.PedidoCantidadPersonas AND P.PedidoCantidadPersonas > 0"}.get(valor, "1=0")
        filas = sgo.filas(f"""
            SELECT TOP 500 P.PedidoNumero, RTRIM(P.PedidoDescripcionCorta) AS descripcion, CONVERT(VARCHAR(10), P.PedidoFecha, 103) AS fecha,
                   P.PedidoCantidadPersonas AS pedidas, ISNULL(A.AsignacionesPorPedido, 0) AS asignadas
            FROM dbo.Pedidos P {ASIG_POR_PEDIDO} WHERE {w} AND {condicion} ORDER BY P.PedidoFecha DESC""", p)
        return respuesta_detalle(f"Pedidos · {valor}", ["Pedido", "Descripción", "Fecha", "Personas pedidas", "Asignadas"], filas)
    condicion = "RTRIM(cb.CausalBajaDescripcion) = %s" if clave == "baja" else "RTRIM(EA.EstadoAsignacionDescripcion) = %s"
    filas = sgo.filas(f"""
        SELECT TOP 500 P.PedidoNumero, RTRIM(c.CandidatoNombre) + ' ' + RTRIM(c.CandidatoApellido) AS candidato,
               RTRIM(EA.EstadoAsignacionDescripcion) AS estado, CONVERT(VARCHAR(10), A.AsignacionFechaIngreso, 103) AS ingreso,
               CONVERT(VARCHAR(10), A.AsignacionFechaEgreso, 103) AS egreso, RTRIM(cb.CausalBajaDescripcion) AS causal
        FROM dbo.Asignaciones A INNER JOIN dbo.Pedidos P ON A.PedidoId = P.PedidoId
        INNER JOIN dbo.Candidatos c ON c.CandidatoId = A.CandidatoId
        INNER JOIN dbo.EstadosAsignacion EA ON EA.EstadoAsignacionId = A.EstadoAsignacionId
        LEFT JOIN dbo.CausalesBaja cb ON cb.CausalBajaId = A.CausalBajaId
        WHERE {w} AND {condicion} ORDER BY A.AsignacionFechaIngreso DESC""", p + [valor])
    return respuesta_detalle(f"Asignaciones · {valor}", ["Pedido", "Candidato", "Estado", "Ingreso", "Egreso", "Causal de baja"], filas)


# ==========================================================================
# 6. Pedidos y asignaciones de un cliente (ana_asi_det)
# ==========================================================================
@catalogo.registrar(
    "pedidos-asignaciones", "Pedidos y asignaciones de un cliente",
    "Cada pedido del cliente con las personas pedidas, las asignaciones por estado y las bajas por causal.",
    usa_periodo=False, icono="bi-list-check", filtros=[F_CLIENTE_PEDIDOS, F_ANIO_DESDE, F_ANIO_HASTA],
)
def pedidos_asignaciones(periodo, filtros):
    cliente_id, por_defecto = _cliente_elegido(filtros, "Pedidos")
    if cliente_id is None:
        return {"kpis": [], "conclusiones": [], "secciones": [seccion("Sin datos", ["No hay pedidos."])]}
    nombre = _nombre_cliente(cliente_id)
    w, p = _where_asig(filtros, cliente_id)
    filas = sgo.filas(f"""
        SELECT P.PedidoId, P.PedidoNumero, RTRIM(P.PedidoDescripcionCorta) AS descripcion_corta,
               CONVERT(VARCHAR(10), P.PedidoFecha, 103) AS fecha_pedido,
               CASE WHEN P.PedidoFechaCierre IS NULL OR P.PedidoFechaCierre <= '1900-01-01' THEN ''
                    ELSE CONVERT(VARCHAR(10), P.PedidoFechaCierre, 103) END AS fecha_cierre,
               P.PedidoCantidadPersonas AS cantidad_pedida, RTRIM(ea.EstadoAsignacionDescripcion) AS estado_asignacion,
               RTRIM(cb.CausalBajaDescripcion) AS causal_baja, COUNT(a.AsignacionId) AS cantidad_asignaciones
        FROM dbo.Pedidos P
        LEFT JOIN dbo.Asignaciones a ON a.PedidoId = P.PedidoId
        LEFT JOIN dbo.EstadosAsignacion ea ON ea.EstadoAsignacionId = a.EstadoAsignacionId
        LEFT JOIN dbo.CausalesBaja cb ON cb.CausalBajaId = a.CausalBajaId
        WHERE {w}
        GROUP BY P.PedidoId, P.PedidoNumero, P.PedidoDescripcionCorta, P.PedidoFecha, P.PedidoFechaCierre, P.PedidoCantidadPersonas,
                 ea.EstadoAsignacionDescripcion, cb.CausalBajaDescripcion
        ORDER BY P.PedidoFecha DESC, P.PedidoId""", p)
    pedidos = {}
    for r in filas:
        pid = r["PedidoId"]
        ped = pedidos.setdefault(pid, {"numero": r["PedidoNumero"], "descripcion": r["descripcion_corta"] or "",
                                       "fecha": r["fecha_pedido"], "cierre": r["fecha_cierre"], "pedidas": num(r["cantidad_pedida"]),
                                       "asignadas": 0, "estados": defaultdict(int), "bajas": defaultdict(int)})
        cantidad = num(r["cantidad_asignaciones"])
        if r.get("estado_asignacion"):
            ped["estados"][r["estado_asignacion"]] += cantidad
            ped["asignadas"] += cantidad
        if r.get("causal_baja"):
            ped["bajas"][r["causal_baja"]] += cantidad
    lista = list(pedidos.values())
    total_pedidas = sum(x["pedidas"] for x in lista)
    total_asig = sum(x["asignadas"] for x in lista)

    def semaforo(x):
        if x["asignadas"] == 0:
            return "🔴 Sin asignar"
        if x["asignadas"] < x["pedidas"]:
            return "🟡 Parcial"
        return "🟢 Completo"

    estados_tot = defaultdict(float)
    for x in lista:
        for e, v in x["estados"].items():
            estados_tot[e] += v
    est = sorted(({"label": e, "value": v} for e, v in estados_tot.items()), key=lambda r: -r["value"])
    aviso = [f"Se muestra {nombre}, el cliente con más pedidos. Elegí otro en Filtros."] if por_defecto else []
    secciones = [
        seccion(
            f"Asignaciones por estado · {nombre}",
            aviso,
            g.ranking(etiquetas(est), valores(est, "value"), "Asignaciones"), alto=g.alto_ranking(len(est), 180),
            explicacion="Todas las asignaciones de los pedidos del cliente, por estado.",
            detalle="estado", ayuda_detalle="Hacé clic en un estado para ver esas asignaciones.",
        ),
        seccion(
            "Pedidos con sus asignaciones",
            ["🟢 completo: asignadas ≥ personas pedidas · 🟡 parcial · 🔴 sin asignaciones."],
            tabla=tabla("Pedidos", ["Pedido", "Descripción", "Fecha", "Cierre", "Pedidas", "Asignadas", "Estado",
                                    "Asignaciones por estado", "Bajas por causal"],
                        [[x["numero"], x["descripcion"], x["fecha"], x["cierre"], entero(x["pedidas"]), entero(x["asignadas"]),
                          semaforo(x), ", ".join(f"{e}: {entero(v)}" for e, v in x["estados"].items()),
                          ", ".join(f"{c}: {entero(v)}" for c, v in x["bajas"].items())] for x in lista[:300]]),
            explicacion="Un renglón por pedido (hasta 300). El detalle de cada asignación se ve haciendo clic en el gráfico de estados.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total pedidos", entero(len(lista))),
            kpi("Personas pedidas", entero(total_pedidas)),
            kpi("Asignaciones", entero(total_asig), pct(proporcion(total_asig, total_pedidas)) + " de cobertura"),
            kpi("Sin asignar", entero(sum(1 for x in lista if x["asignadas"] == 0)), "pedidos",
                alerta=any(x["asignadas"] == 0 for x in lista)),
        ],
        "conclusiones": [
            f"{nombre}: {entero(len(lista))} pedidos, {entero(total_pedidas)} personas pedidas y {entero(total_asig)} asignaciones.",
            f"{entero(sum(1 for x in lista if x['asignadas'] == 0))} pedidos no tienen asignaciones.",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué pedidos de este cliente quedaron sin cubrir?"],
        "contexto_ia": {"cliente": nombre, "pedidos": len(lista), "pedidas": total_pedidas, "asignaciones": total_asig},
    }


@catalogo.detalle("pedidos-asignaciones")
def detalle_pedidos_asignaciones(clave, valor, serie, periodo, filtros):
    cliente_id, _ = _cliente_elegido(filtros, "Pedidos")
    w, p = _where_asig(filtros, cliente_id)
    filas = sgo.filas(f"""
        SELECT TOP 500 P.PedidoNumero, a.AsignacionId, RTRIM(c.CandidatoNombre) AS nombre, RTRIM(c.CandidatoApellido) AS apellido,
               CONVERT(VARCHAR(10), a.AsignacionFechaIngreso, 103) AS ingreso, CONVERT(VARCHAR(10), a.AsignacionFechaEgreso, 103) AS egreso,
               RTRIM(cb.CausalBajaDescripcion) AS causal
        FROM dbo.Asignaciones a INNER JOIN dbo.Pedidos P ON P.PedidoId = a.PedidoId
        INNER JOIN dbo.Candidatos c ON c.CandidatoId = a.CandidatoId
        INNER JOIN dbo.EstadosAsignacion ea ON ea.EstadoAsignacionId = a.EstadoAsignacionId
        LEFT JOIN dbo.CausalesBaja cb ON cb.CausalBajaId = a.CausalBajaId
        WHERE {w} AND LTRIM(RTRIM(ea.EstadoAsignacionDescripcion)) = %s
        ORDER BY a.AsignacionFechaIngreso DESC""", p + [valor.strip()])
    return respuesta_detalle(f"Asignaciones · {valor}", ["Pedido", "Asignación", "Nombre", "Apellido", "Ingreso", "Egreso",
                                                         "Causal de baja"], filas)
