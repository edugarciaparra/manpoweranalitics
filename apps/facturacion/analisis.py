"""
Análisis del módulo Facturación: las 6 pantallas de Órdenes de facturación del
SGO (ord_res, ord_cli, ord_tem, ord_per, ord_por, ord_seg) con el mismo SQL y
filtros, y las órdenes de cada gráfico en el modal.

Los montos se suman como en el SGO, sin convertir monedas: para no mezclar,
conviene filtrar por moneda. Los indicadores muestran la moneda principal.
"""
from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta

from apps.core import graficos as g
from apps.core import sgo
from apps.core.analisis import Catalogo, seccion
from apps.core.filtros import Filtro
from apps.core.pantalla import (
    concentracion, decimal, detalle as respuesta_detalle, entero, etiquetas, extremos, kpi, lider, pct,
    proporcion, tabla, total, valores,
)
from apps.core.sgo import num

from . import services as s
from .services import DESDE, where

catalogo = Catalogo()

MESES_TENDENCIA = Filtro.fijo("meses_tendencia", "Meses de tendencia", {"6": "6", "12": "12", "24": "24", "36": "36"}, "12")
AVISO_MONEDA = "Los montos se suman sin convertir monedas; filtrá por moneda para no mezclarlas."


def _f_monto(simbolo):
    return lambda v: s.monto(v, simbolo)


# ==========================================================================
# 1. Revenue general (ord_res)
# ==========================================================================
_RANGO_MONTO = """CASE
    WHEN o.OrdenMonto < 10000 THEN 'Menos de $10K'
    WHEN o.OrdenMonto BETWEEN 10000 AND 49999 THEN '$10K - $50K'
    WHEN o.OrdenMonto BETWEEN 50000 AND 99999 THEN '$50K - $100K'
    ELSE 'Más de $100K' END"""
_CONDICION_MONTO = {"Menos de $10K": "o.OrdenMonto < 10000", "$10K - $50K": "o.OrdenMonto BETWEEN 10000 AND 49999",
                    "$50K - $100K": "o.OrdenMonto BETWEEN 50000 AND 99999", "Más de $100K": "o.OrdenMonto >= 100000"}


@catalogo.registrar(
    "revenue", "Revenue general",
    "Cuánto se factura, cómo evoluciona por mes y qué divisiones, servicios y clientes lo explican.",
    usa_periodo=False, icono="bi-cash-coin", filtros=s.FILTROS_ANIO + [MESES_TENDENCIA],
)
def revenue(periodo, filtros):
    w, p = where(filtros)
    mon = s.moneda_principal(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_ordenes, ISNULL(SUM(o.OrdenMonto), 0) AS total_facturado,
               ROUND(ISNULL(AVG(o.OrdenMonto), 0), 2) AS ticket_promedio, COUNT(DISTINCT p.ClienteId) AS clientes_activos,
               ROUND(CAST(ISNULL(SUM(o.OrdenMonto), 0) AS FLOAT)
                     / NULLIF(DATEDIFF(MONTH, MIN(o.OrdenFecha), MAX(o.OrdenFecha)) + 1, 0), 2) AS facturacion_mensual_promedio
        {DESDE} WHERE {w}""", p)
    desde = date.today() - relativedelta(months=int(filtros.get("meses_tendencia") or 12))
    # La tendencia mira los últimos N meses aunque el rango de fechas del filtro sea el año en curso
    filtros_tendencia = dict(filtros, fecha_desde=None, fecha_hasta=None)
    wt, pt = where(filtros_tendencia)
    tendencia = sgo.filas(f"""
        SELECT CAST(YEAR(o.OrdenFecha) AS VARCHAR(4)) + '-' + RIGHT('0' + CAST(MONTH(o.OrdenFecha) AS VARCHAR(2)), 2) AS mes,
               COUNT(*) AS total_ordenes, ISNULL(SUM(o.OrdenMonto), 0) AS total_facturado
        {DESDE} WHERE {wt} AND o.OrdenFecha >= %s
        GROUP BY CAST(YEAR(o.OrdenFecha) AS VARCHAR(4)) + '-' + RIGHT('0' + CAST(MONTH(o.OrdenFecha) AS VARCHAR(2)), 2)
        ORDER BY mes""", pt + [desde])
    por_division = sgo.filas(f"""
        SELECT d.DivisionDescripcion AS label, COUNT(*) AS total_ordenes, ISNULL(SUM(o.OrdenMonto), 0) AS total_facturado
        {DESDE} WHERE {w} GROUP BY d.DivisionDescripcion ORDER BY total_facturado DESC""", p)
    servicios = sgo.filas(f"""
        SELECT TOP 10 sv.ServicioDescripcion AS label, COUNT(*) AS total_ordenes, ISNULL(SUM(o.OrdenMonto), 0) AS total_facturado
        {DESDE} INNER JOIN dbo.Servicios sv ON o.OrdenServicioId = sv.ServicioId
        WHERE {w} GROUP BY sv.ServicioId, sv.ServicioDescripcion ORDER BY total_facturado DESC""", p)
    clientes = sgo.filas(f"""
        SELECT TOP 10 c.ClienteNombre AS label, COUNT(*) AS total_ordenes, ISNULL(SUM(o.OrdenMonto), 0) AS total_facturado
        {DESDE} INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
        WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre ORDER BY total_facturado DESC""", p)
    montos = sgo.filas(f"""
        SELECT {_RANGO_MONTO} AS label, COUNT(*) AS value, MIN(o.OrdenMonto) AS orden
        {DESDE} WHERE {w} GROUP BY {_RANGO_MONTO} ORDER BY orden""", p)

    fm = _f_monto(mon)
    pico = max(tendencia, key=lambda r: num(r.get("total_facturado")), default=None)
    secciones = [
        seccion(
            f"Tendencia mensual de facturación (últimos {filtros.get('meses_tendencia') or 12} meses)",
            [f"El mes de mayor facturación fue {pico['mes']}: {fm(pico['total_facturado'])} en "
             f"{entero(pico['total_ordenes'])} órdenes." if pico else "", AVISO_MONEDA],
            g.lineas([r["mes"] for r in tendencia], {"Facturado": valores(tendencia, "total_facturado")},
                     formato="fmt:pesos_k", area=True),
            explicacion="Suma de OrdenMonto por mes de OrdenFecha. Respeta los filtros salvo el rango de fechas: "
                        "siempre muestra los últimos meses elegidos.",
        ),
        seccion(
            "Facturación por división",
            [lider(por_division, "label", "total_facturado", "", "lo facturado").replace(" encabeza con ", " encabeza: ")],
            g.ranking(etiquetas(por_division), valores(por_division, "total_facturado"), "Facturado", formato="fmt:pesos_k"),
            alto=g.alto_ranking(len(por_division)),
            explicacion="Monto facturado por la división del pedido de cada orden.",
            detalle="division", ayuda_detalle="Hacé clic en una división para ver sus órdenes.",
            tabla=tabla("Por división", ["División", "Órdenes", "Facturado"],
                        [[r["label"], entero(r["total_ordenes"]), fm(r["total_facturado"])] for r in por_division]),
        ),
        seccion(
            "Top 10 servicios por revenue",
            [concentracion(servicios, "total_facturado", 3, "lo facturado por el top 10")],
            g.ranking(etiquetas(servicios), valores(servicios, "total_facturado"), "Facturado", g.SERIES[2],
                      formato="fmt:pesos_k"),
            alto=g.alto_ranking(len(servicios)),
            explicacion="Servicios de las órdenes (OrdenServicioId) ordenados por monto facturado.",
            detalle="servicio", ayuda_detalle="Hacé clic en un servicio para ver sus órdenes.",
        ),
        seccion(
            "Top 10 clientes por facturación",
            [concentracion(clientes, "total_facturado", 3, "lo facturado por el top 10")],
            g.ranking(etiquetas(clientes), valores(clientes, "total_facturado"), "Facturado", g.SERIES[1],
                      formato="fmt:pesos_k"),
            alto=g.alto_ranking(len(clientes)),
            explicacion="Los 10 clientes con mayor monto facturado.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus órdenes.",
        ),
        seccion(
            "Distribución por rango de montos",
            [lider(montos, "label", "value", "órdenes")],
            g.columnas(etiquetas(montos), {"Órdenes": valores(montos, "value")}, rotar=0),
            explicacion="Cuántas órdenes hay de menos de $10K, entre $10K y $50K, entre $50K y $100K y de más de $100K.",
            detalle="rango", ayuda_detalle="Hacé clic en un rango para ver esas órdenes.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total órdenes", entero(k.get("total_ordenes"))),
            kpi("Total facturado", s.monto_corto(k.get("total_facturado"), mon), f"moneda principal {mon}",
                "Suma de OrdenMonto. " + AVISO_MONEDA),
            kpi("Ticket promedio", fm(k.get("ticket_promedio")), "", "Monto promedio por orden."),
            kpi("Clientes activos", entero(k.get("clientes_activos")), "con órdenes"),
            kpi("Facturación mensual", s.monto_corto(k.get("facturacion_mensual_promedio"), mon), "promedio",
                "Total facturado ÷ meses entre la primera y la última orden del filtro."),
        ],
        "conclusiones": [
            f"Se facturaron {fm(k.get('total_facturado'))} en {entero(k.get('total_ordenes'))} órdenes de "
            f"{entero(k.get('clientes_activos'))} clientes.",
            lider(por_division, "label", "total_facturado", "", "lo facturado").replace(" encabeza con ", " encabeza: "),
            concentracion(clientes, "total_facturado", 3, "lo facturado por el top 10 de clientes"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué servicios facturan más?", "¿Cómo viene la facturación mensual?"],
        "contexto_ia": {"kpis": k, "moneda": mon, "tendencia": tendencia, "por_division": por_division,
                        "servicios": servicios, "clientes": clientes, "montos": montos},
    }


@catalogo.detalle("revenue")
def detalle_revenue(clave, valor, serie, periodo, filtros):
    condicion, params, orden = {"division": "d.DivisionDescripcion = %s", "servicio": "s.ServicioDescripcion = %s",
                                "cliente": "c.ClienteNombre = %s"}.get(clave, ""), [valor], "o.OrdenFecha DESC"
    if clave == "rango":
        condicion, params, orden = _CONDICION_MONTO.get(valor, "1=0"), [], "o.OrdenMonto DESC, o.OrdenFecha DESC"
    return respuesta_detalle(f"Órdenes · {valor}", s.COLUMNAS_ORDEN, s.ordenes(filtros, condicion, params, orden=orden))


# ==========================================================================
# 2. Análisis de clientes (ord_cli)
# ==========================================================================
@catalogo.registrar(
    "clientes", "Análisis de clientes",
    "Qué clientes generan el revenue, cuán concentrado está (ABC), con qué frecuencia compran y su ticket.",
    usa_periodo=False, icono="bi-people", filtros=s.FILTROS,
)
def clientes(periodo, filtros):
    w, p = where(filtros)
    mon = s.moneda_principal(filtros)
    fm = _f_monto(mon)
    k = sgo.fila(f"""
        SELECT COUNT(DISTINCT c.ClienteId) AS total_clientes, SUM(o.OrdenMonto) AS revenue_total,
               CASE WHEN COUNT(DISTINCT c.ClienteId) > 0 THEN SUM(o.OrdenMonto) / COUNT(DISTINCT c.ClienteId) ELSE 0 END AS revenue_promedio_cliente
        {DESDE} INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId WHERE {w}""", p)
    por_cliente = sgo.filas(f"""
        SELECT c.ClienteId AS cliente_id, RTRIM(c.ClienteNombre) AS label, SUM(o.OrdenMonto) AS revenue_total,
               COUNT(*) AS total_ordenes, COUNT(DISTINCT o.OrdenServicioId) AS total_servicios, AVG(o.OrdenMonto) AS ticket_promedio
        {DESDE} INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
        WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre ORDER BY revenue_total DESC""", p)
    abc = sgo.filas(f"""
        SELECT segmento, COUNT(*) AS cantidad_clientes, SUM(revenue) AS revenue_total,
               CAST(100.0 * SUM(revenue) / NULLIF(SUM(SUM(revenue)) OVER (), 0) AS DECIMAL(10,2)) AS porcentaje_revenue
        FROM (SELECT c.ClienteId, SUM(o.OrdenMonto) AS revenue, NTILE(5) OVER (ORDER BY SUM(o.OrdenMonto) DESC) AS quintil
              {DESDE} INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
              WHERE {w} GROUP BY c.ClienteId) ranked
        CROSS APPLY (SELECT CASE WHEN quintil = 1 THEN 'A' WHEN quintil IN (2, 3) THEN 'B' ELSE 'C' END AS segmento) seg
        GROUP BY segmento ORDER BY segmento""", p)
    frecuencia = sgo.filas(f"""
        SELECT rango AS label, COUNT(*) AS cantidad_clientes, MIN(total_ordenes) AS orden
        FROM (SELECT c.ClienteId, COUNT(*) AS total_ordenes,
                     CASE WHEN COUNT(*) = 1 THEN '1 orden' WHEN COUNT(*) BETWEEN 2 AND 5 THEN '2-5 órdenes'
                          WHEN COUNT(*) BETWEEN 6 AND 10 THEN '6-10 órdenes' WHEN COUNT(*) BETWEEN 11 AND 20 THEN '11-20 órdenes'
                          ELSE '20+ órdenes' END AS rango
              {DESDE} INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
              WHERE {w} GROUP BY c.ClienteId) freq
        GROUP BY rango ORDER BY orden""", p)

    top20 = por_cliente[:20]
    por_volumen = sorted(por_cliente, key=lambda r: -num(r["total_ordenes"]))[:20]
    recurrentes = sum(1 for r in por_cliente if num(r["total_ordenes"]) >= 2)
    tasa_recurrencia = proporcion(recurrentes, len(por_cliente))
    revenue_total = total(por_cliente, "revenue_total")
    top_n = max(1, round(len(por_cliente) * 0.2))
    conc_top20 = proporcion(total(por_cliente[:top_n], "revenue_total"), revenue_total)
    seg_a = next((r for r in abc if r.get("segmento") == "A"), None)

    secciones = [
        seccion(
            "Top 20 clientes por revenue",
            [concentracion(top20, "revenue_total", 3, "revenue del top 20")],
            g.ranking(etiquetas(top20), valores(top20, "revenue_total"), "Revenue", formato="fmt:pesos_k"),
            alto=g.alto_ranking(len(top20)),
            explicacion="Los 20 clientes con mayor monto facturado.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus órdenes.",
            tabla=tabla("Top 20 por revenue", ["Cliente", "Revenue", "Órdenes", "Servicios", "Ticket promedio"],
                        [[r["label"], fm(r["revenue_total"]), entero(r["total_ordenes"]), entero(r["total_servicios"]),
                          fm(r["ticket_promedio"])] for r in top20]),
        ),
        seccion(
            "Top 20 clientes por volumen de órdenes",
            [lider(por_volumen, "label", "total_ordenes", "órdenes", "el top 20")],
            g.ranking(etiquetas(por_volumen), valores(por_volumen, "total_ordenes"), "Órdenes", g.SERIES[1]),
            alto=g.alto_ranking(len(por_volumen)),
            explicacion="Los 20 clientes con más órdenes de facturación, sin importar el monto.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus órdenes.",
        ),
        seccion(
            "Distribución ABC (Pareto)",
            [f"Los clientes A (el 20% que más factura) generan el {pct(seg_a['porcentaje_revenue'])} del revenue."
             if seg_a else ""],
            g.columnas([f"Segmento {r['segmento']}" for r in abc], {"% del revenue": valores(abc, "porcentaje_revenue")},
                       formato="fmt:pct", rotar=0, colores=[g.SERIES[0]]),
            explicacion="Los clientes se ordenan por revenue y se parten en quintos: A es el primer quinto, B el "
                        "segundo y tercero, C el resto. Cada barra muestra qué parte del revenue aporta el segmento.",
            tabla=tabla("Segmentos ABC", ["Segmento", "Clientes", "Revenue", "% del revenue"],
                        [[r["segmento"], entero(r["cantidad_clientes"]), fm(r["revenue_total"]), pct(r["porcentaje_revenue"])]
                         for r in abc]),
        ),
        seccion(
            "Frecuencia de órdenes",
            [lider(frecuencia, "label", "cantidad_clientes", "clientes")],
            g.columnas(etiquetas(frecuencia), {"Clientes": valores(frecuencia, "cantidad_clientes")}, rotar=0),
            explicacion="Clientes agrupados según cuántas órdenes de facturación tienen.",
            detalle="frecuencia", ayuda_detalle="Hacé clic en un rango para ver los clientes.",
        ),
        seccion(
            "Matriz de valor: ticket promedio vs. volumen",
            ["Arriba a la derecha están los clientes con muchas órdenes y ticket alto; abajo a la izquierda, los de "
             "poco volumen y ticket bajo."],
            g.dispersion([(num(r["total_ordenes"]), num(r["ticket_promedio"]), r["label"]) for r in por_cliente[:100]],
                         "Órdenes", "Ticket promedio", formato_y="fmt:pesos_k"),
            alto=380,
            explicacion="Cada punto es uno de los 100 clientes con más revenue: a la derecha más órdenes, arriba "
                        "mayor ticket promedio. Pasá el mouse para ver el nombre.",
            detalle="cliente_punto", ayuda_detalle="Hacé clic en un punto para ver las órdenes del cliente.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total clientes", entero(k.get("total_clientes"))),
            kpi("Revenue total", s.monto_corto(k.get("revenue_total"), mon), "", AVISO_MONEDA),
            kpi("Revenue por cliente", s.monto_corto(k.get("revenue_promedio_cliente"), mon), "promedio"),
            kpi("Tasa de recurrencia", pct(tasa_recurrencia), "clientes con 2+ órdenes",
                "Clientes con dos o más órdenes ÷ total de clientes × 100."),
            kpi("Concentración top 20%", pct(conc_top20), f"{entero(top_n)} clientes",
                "Parte del revenue que aporta el 20% de clientes que más factura."),
        ],
        "conclusiones": [
            f"El 20% de los clientes ({entero(top_n)}) genera el {pct(conc_top20)} del revenue.",
            f"{pct(tasa_recurrencia)} de los clientes tiene más de una orden.",
            lider(top20, "label", "revenue_total", "", "el revenue del top 20").replace(" encabeza con ", " encabeza "),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Cuánto dependemos de los clientes A?", "¿Qué clientes compran una sola vez?"],
        "contexto_ia": {"kpis": k, "abc": abc, "frecuencia": frecuencia, "top20": top20,
                        "tasa_recurrencia": tasa_recurrencia, "concentracion_top20": conc_top20},
    }


_CONDICION_FRECUENCIA = {"1 orden": "COUNT(*) = 1", "2-5 órdenes": "COUNT(*) BETWEEN 2 AND 5",
                         "6-10 órdenes": "COUNT(*) BETWEEN 6 AND 10", "11-20 órdenes": "COUNT(*) BETWEEN 11 AND 20",
                         "20+ órdenes": "COUNT(*) > 20"}


@catalogo.detalle("clientes")
def detalle_clientes(clave, valor, serie, periodo, filtros):
    if clave == "frecuencia":
        w, p = where(filtros)
        filas = sgo.filas(f"""
            SELECT TOP 500 RTRIM(c.ClienteNombre) AS cliente, COUNT(*) AS ordenes, SUM(o.OrdenMonto) AS revenue,
                   CONVERT(VARCHAR(10), MIN(o.OrdenFecha), 103) AS primera, CONVERT(VARCHAR(10), MAX(o.OrdenFecha), 103) AS ultima
            {DESDE} INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
            WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre HAVING {_CONDICION_FRECUENCIA.get(valor, '1=0')}
            ORDER BY revenue DESC""", p)
        return respuesta_detalle(f"Clientes · {valor}", ["Cliente", "Órdenes", "Revenue", "Primera orden", "Última orden"], filas)
    filas = s.ordenes(filtros, "RTRIM(c.ClienteNombre) = %s", [valor.strip()])
    return respuesta_detalle(f"Órdenes de {valor}", s.COLUMNAS_ORDEN, filas)


# ==========================================================================
# 3. Análisis temporal (ord_tem)
# ==========================================================================
@catalogo.registrar(
    "temporal", "Análisis temporal",
    "Evolución mensual y trimestral del revenue, su estabilidad y la tasa de crecimiento mes a mes.",
    usa_periodo=False, icono="bi-calendar3", filtros=s.FILTROS,
)
def temporal(periodo, filtros):
    w, p = where(filtros)
    mon = s.moneda_principal(filtros)
    fm = _f_monto(mon)
    k = sgo.fila(f"""
        SELECT AVG(revenue_mensual) AS revenue_mensual_promedio,
               STDEV(revenue_mensual) / NULLIF(AVG(revenue_mensual), 0) * 100 AS coef_variacion
        FROM (SELECT YEAR(o.OrdenFecha) AS anio, MONTH(o.OrdenFecha) AS mes, SUM(o.OrdenMonto) AS revenue_mensual
              {DESDE} WHERE {w} GROUP BY YEAR(o.OrdenFecha), MONTH(o.OrdenFecha)) mensual""", p)
    mensual = sgo.filas(f"""
        SELECT CONCAT(CAST(YEAR(o.OrdenFecha) AS VARCHAR), '-', RIGHT('0' + CAST(MONTH(o.OrdenFecha) AS VARCHAR), 2)) AS mes,
               SUM(o.OrdenMonto) AS revenue, COUNT(*) AS total_ordenes,
               LAG(SUM(o.OrdenMonto)) OVER (ORDER BY YEAR(o.OrdenFecha), MONTH(o.OrdenFecha)) AS revenue_anterior
        {DESDE} WHERE {w} GROUP BY YEAR(o.OrdenFecha), MONTH(o.OrdenFecha)
        ORDER BY YEAR(o.OrdenFecha), MONTH(o.OrdenFecha)""", p)
    trimestral = sgo.filas(f"""
        SELECT YEAR(o.OrdenFecha) AS anio, DATEPART(QUARTER, o.OrdenFecha) AS trimestre, SUM(o.OrdenMonto) AS revenue,
               COUNT(*) AS total_ordenes, COUNT(DISTINCT p.ClienteId) AS total_clientes
        {DESDE} WHERE {w} GROUP BY YEAR(o.OrdenFecha), DATEPART(QUARTER, o.OrdenFecha) ORDER BY anio, trimestre""", p)

    crecimiento = [{"mes": r["mes"], "pct": round(proporcion(num(r["revenue"]) - num(r["revenue_anterior"]),
                                                              r["revenue_anterior"]), 1)}
                   for r in mensual if num(r.get("revenue_anterior"))]
    por_anio = defaultdict(lambda: [None] * 4)
    for r in trimestral:
        t = int(num(r["trimestre"]) or 1)
        if 1 <= t <= 4:
            por_anio[str(int(num(r["anio"])))][t - 1] = num(r["revenue"])
    anios = sorted(por_anio)[-4:]
    cv = num(k.get("coef_variacion"))
    estabilidad = "estable" if cv < 20 else "con variaciones moderadas" if cv < 40 else "muy variable"
    grafico_crec = g.columnas([r["mes"] for r in crecimiento], {"Crecimiento": [r["pct"] for r in crecimiento]},
                              formato="fmt:pct")
    grafico_crec["series"][0]["data"] = [{"value": r["pct"], "itemStyle": {"color": g.POSITIVO if r["pct"] >= 0 else g.NEGATIVO}}
                                         for r in crecimiento]
    subas = sum(1 for r in crecimiento if r["pct"] > 0)
    pico = max(mensual, key=lambda r: num(r["revenue"]), default=None)

    secciones = [
        seccion(
            "Tendencia de revenue mensual",
            [f"El mejor mes fue {pico['mes']} con {fm(pico['revenue'])}." if pico else "",
             f"El revenue mensual es {estabilidad} (coeficiente de variación {pct(cv)})."],
            g.lineas([r["mes"] for r in mensual], {"Revenue": valores(mensual, "revenue")}, formato="fmt:pesos_k", area=True),
            explicacion="Suma de OrdenMonto por mes en todo el rango filtrado.",
            detalle="mes", ayuda_detalle="Hacé clic en un mes para ver sus órdenes.",
        ),
        seccion(
            "Revenue trimestral por año",
            [],
            g.columnas(["T1", "T2", "T3", "T4"], {a: por_anio[a] for a in anios}, formato="fmt:pesos_k", rotar=0),
            explicacion="Cada grupo es un trimestre y cada color un año, para comparar el mismo trimestre entre años.",
            tabla=tabla("Por trimestre", ["Año", "Trimestre", "Revenue", "Órdenes", "Clientes"],
                        [[int(num(r["anio"])), f"T{int(num(r['trimestre']))}", fm(r["revenue"]), entero(r["total_ordenes"]),
                          entero(r["total_clientes"])] for r in trimestral]),
        ),
        seccion(
            "Tasa de crecimiento mensual",
            [f"El revenue creció respecto del mes anterior en {subas} de {len(crecimiento)} meses." if crecimiento else ""],
            grafico_crec,
            explicacion="Variación porcentual del revenue de cada mes contra el mes anterior: azul si subió, rojo si bajó.",
        ),
    ]
    return {
        "kpis": [
            kpi("Revenue mensual promedio", s.monto_corto(k.get("revenue_mensual_promedio"), mon), "", AVISO_MONEDA),
            kpi("Coeficiente de variación", pct(cv), estabilidad,
                "Desvío estándar del revenue mensual ÷ promedio × 100. Menos de 20% es estable.", alerta=cv >= 40),
            kpi("Moneda principal", mon, "la de más órdenes"),
            kpi("Meses con suba", f"{subas} de {len(crecimiento)}", "contra el mes anterior"),
        ],
        "conclusiones": [
            f"El revenue promedio es {fm(k.get('revenue_mensual_promedio'))} por mes y es {estabilidad}.",
            f"El mejor mes fue {pico['mes']} ({fm(pico['revenue'])})." if pico else "",
            f"Hubo suba en {subas} de {len(crecimiento)} meses." if crecimiento else "",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Hay estacionalidad en la facturación?", "¿Qué trimestre es el más fuerte?"],
        "contexto_ia": {"kpis": k, "mensual": mensual, "trimestral": trimestral, "crecimiento": crecimiento},
    }


@catalogo.detalle("temporal")
def detalle_temporal(clave, valor, serie, periodo, filtros):
    filas = s.ordenes(filtros, "FORMAT(o.OrdenFecha, 'yyyy-MM') = %s", [valor], orden="o.OrdenMonto DESC")
    return respuesta_detalle(f"Órdenes de {valor}", s.COLUMNAS_ORDEN, filas)


# ==========================================================================
# 4. Performance de responsables (ord_per)
# ==========================================================================
_RESPONSABLE = "RTRIM(ISNULL(e.EjecutivoCuentaNombreAbreviado, e.EjecutivoCuentaNombre + ' ' + e.EjecutivoCuentaApellido))"
_JOIN_RESP = "LEFT JOIN dbo.EjecutivosCuenta e ON o.OrdenResponsableId = e.EjecutivoCuentaId"
_GRUPO_RESP = "o.OrdenResponsableId, e.EjecutivoCuentaNombreAbreviado, e.EjecutivoCuentaNombre, e.EjecutivoCuentaApellido"


@catalogo.registrar(
    "responsables", "Performance de responsables",
    "Revenue, volumen y ticket de cada responsable de facturación, su mix de servicios y cómo se reparte la cartera.",
    usa_periodo=False, icono="bi-person-workspace", filtros=s.FILTROS,
)
def responsables(periodo, filtros):
    w, p = where(filtros)
    mon = s.moneda_principal(filtros)
    fm = _f_monto(mon)
    k = sgo.fila(f"""
        SELECT COUNT(DISTINCT o.OrdenResponsableId) AS total_responsables,
               SUM(o.OrdenMonto) / NULLIF(COUNT(DISTINCT o.OrdenResponsableId), 0) AS revenue_promedio_responsable,
               COUNT(*) / NULLIF(COUNT(DISTINCT o.OrdenResponsableId), 0) AS ordenes_promedio_responsable,
               AVG(o.OrdenMonto) AS ticket_promedio_responsable
        {DESDE} WHERE {w}""", p)
    ranking = sgo.filas(f"""
        SELECT {_RESPONSABLE} AS label, SUM(o.OrdenMonto) AS revenue_total, COUNT(*) AS total_ordenes,
               COUNT(DISTINCT p.ClienteId) AS total_clientes, AVG(o.OrdenMonto) AS ticket_promedio,
               CAST(100.0 * SUM(o.OrdenMonto) / NULLIF(SUM(SUM(o.OrdenMonto)) OVER (), 0) AS DECIMAL(10,2)) AS porcentaje_revenue
        {DESDE} {_JOIN_RESP} WHERE {w} GROUP BY {_GRUPO_RESP}
        HAVING SUM(o.OrdenMonto) > 0 ORDER BY revenue_total DESC""", p)
    mix = sgo.filas(f"""
        WITH TopResp AS (SELECT TOP 15 o.OrdenResponsableId {DESDE} WHERE {w}
                         GROUP BY o.OrdenResponsableId ORDER BY SUM(o.OrdenMonto) DESC)
        SELECT {_RESPONSABLE} AS responsable_nombre, RTRIM(sv.ServicioDescripcion) AS servicio_nombre, SUM(o.OrdenMonto) AS revenue
        {DESDE} {_JOIN_RESP}
        INNER JOIN dbo.Servicios sv ON o.OrdenServicioId = sv.ServicioId
        INNER JOIN TopResp tr ON o.OrdenResponsableId = tr.OrdenResponsableId
        WHERE {w}
        GROUP BY e.EjecutivoCuentaNombreAbreviado, e.EjecutivoCuentaNombre, e.EjecutivoCuentaApellido, sv.ServicioDescripcion
        ORDER BY responsable_nombre, revenue DESC""", p + p)

    top20 = ranking[:20]
    por_volumen = sorted(ranking, key=lambda r: -num(r["total_ordenes"]))[:20]
    resp = list(dict.fromkeys(str(r["responsable_nombre"] or "Sin responsable") for r in mix))
    serv = list(dict.fromkeys(str(r["servicio_nombre"] or "Sin servicio") for r in mix))[:12]
    celdas = [[serv.index(str(r["servicio_nombre"])), resp.index(str(r["responsable_nombre"] or "Sin responsable")),
               round(num(r["revenue"]))] for r in mix if str(r["servicio_nombre"]) in serv]
    top3 = sum(num(r["porcentaje_revenue"]) for r in ranking[:3])

    secciones = [
        seccion(
            "Top 20 responsables por revenue",
            [concentracion(top20, "revenue_total", 3, "revenue del top 20")],
            g.ranking(etiquetas(top20), valores(top20, "revenue_total"), "Revenue", formato="fmt:pesos_k"),
            alto=g.alto_ranking(len(top20)),
            explicacion="Responsable de la orden (OrdenResponsableId → EjecutivosCuenta) por monto facturado.",
            detalle="responsable", ayuda_detalle="Hacé clic en un responsable para ver sus órdenes.",
            tabla=tabla("Top 20 por revenue", ["Responsable", "Revenue", "Órdenes", "Clientes", "Ticket promedio"],
                        [[r["label"], fm(r["revenue_total"]), entero(r["total_ordenes"]), entero(r["total_clientes"]),
                          fm(r["ticket_promedio"])] for r in top20]),
        ),
        seccion(
            "Top 20 responsables por volumen",
            [lider(por_volumen, "label", "total_ordenes", "órdenes", "el top 20")],
            g.ranking(etiquetas(por_volumen), valores(por_volumen, "total_ordenes"), "Órdenes", g.SERIES[1]),
            alto=g.alto_ranking(len(por_volumen)),
            explicacion="Los mismos responsables ordenados por cantidad de órdenes.",
            detalle="responsable", ayuda_detalle="Hacé clic en un responsable para ver sus órdenes.",
        ),
        seccion(
            "Matriz de performance",
            ["A la derecha los que emiten más órdenes; arriba los de ticket más alto."],
            g.dispersion([(num(r["total_ordenes"]), num(r["ticket_promedio"]), r["label"])
                          for r in ranking[:50] if num(r["total_ordenes"]) >= 5],
                         "Órdenes", "Ticket promedio", formato_y="fmt:pesos_k"),
            alto=380,
            explicacion="Cada punto es un responsable con 5 órdenes o más (hasta 50): órdenes en el eje horizontal y "
                        "ticket promedio en el vertical.",
            detalle="responsable_punto", ayuda_detalle="Hacé clic en un punto para ver las órdenes del responsable.",
        ),
        seccion(
            "Servicios por responsable",
            [],
            g.mapa_calor(serv, resp, celdas), alto=max(320, 30 * len(resp) + 120),
            explicacion="Revenue de cada servicio (columnas) para los 15 responsables que más facturan (filas). "
                        "Cuanto más oscuro, más revenue.",
        ),
        seccion(
            "Distribución de cartera",
            [f"Los 3 primeros responsables concentran el {pct(top3)} del revenue." if len(ranking) > 3 else ""],
            g.ranking(etiquetas(ranking[:25]), valores(ranking[:25], "porcentaje_revenue"), "% del revenue",
                      g.SERIES[3], formato="fmt:pct"),
            alto=g.alto_ranking(min(len(ranking), 25)),
            explicacion="Qué parte del revenue total maneja cada responsable.",
            detalle="responsable", ayuda_detalle="Hacé clic en un responsable para ver sus órdenes.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total responsables", entero(k.get("total_responsables"))),
            kpi("Revenue por responsable", s.monto_corto(k.get("revenue_promedio_responsable"), mon), "promedio", AVISO_MONEDA),
            kpi("Órdenes por responsable", entero(k.get("ordenes_promedio_responsable")), "promedio"),
            kpi("Ticket promedio", fm(k.get("ticket_promedio_responsable"))),
        ],
        "conclusiones": [
            lider(ranking, "label", "revenue_total", "", "el revenue").replace(" encabeza con ", " encabeza "),
            f"Los 3 primeros responsables manejan el {pct(top3)} del revenue." if len(ranking) > 3 else "",
            f"Cada responsable emite en promedio {entero(k.get('ordenes_promedio_responsable'))} órdenes.",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Quién tiene el ticket más alto?", "¿La cartera está muy concentrada?"],
        "contexto_ia": {"kpis": k, "ranking": ranking[:20]},
    }


@catalogo.detalle("responsables")
def detalle_responsables(clave, valor, serie, periodo, filtros):
    filas = s.ordenes(filtros, f"{_RESPONSABLE} = %s", [valor.strip()], joins=_JOIN_RESP)
    return respuesta_detalle(f"Órdenes de {valor}", s.COLUMNAS_ORDEN, filas)


# ==========================================================================
# 5. Análisis de portafolio (ord_por)
# ==========================================================================
@catalogo.registrar(
    "portafolio", "Análisis de portafolio",
    "Qué servicios explican el revenue (Pareto), cómo cambia su participación y en qué divisiones se venden.",
    usa_periodo=False, icono="bi-grid-3x3-gap",
    filtros=[s.F_DIVISIONES, s.F_ESTADO, s.F_CLIENTE, s.F_MONEDA, s.F_DESDE, s.F_HASTA],
)
def portafolio(periodo, filtros):
    w, p = where(filtros)
    mon = s.moneda_principal(filtros)
    fm = _f_monto(mon)
    join_s = "INNER JOIN dbo.Servicios sv ON o.OrdenServicioId = sv.ServicioId"
    servicios = sgo.filas(f"""
        SELECT RTRIM(sv.ServicioDescripcion) AS label, SUM(o.OrdenMonto) AS revenue, COUNT(*) AS total_ordenes,
               COUNT(DISTINCT p.ClienteId) AS total_clientes, AVG(o.OrdenMonto) AS ticket_promedio,
               COUNT(DISTINCT d.DivisionId) AS diversificacion_divisiones,
               CAST(100.0 * SUM(o.OrdenMonto) / NULLIF(SUM(SUM(o.OrdenMonto)) OVER (), 0) AS DECIMAL(10,2)) AS porcentaje_revenue
        {DESDE} {join_s} WHERE {w} GROUP BY sv.ServicioId, sv.ServicioDescripcion ORDER BY revenue DESC""", p)
    penetracion = sgo.filas(f"""
        SELECT RTRIM(d.DivisionDescripcion) AS division_nombre, RTRIM(sv.ServicioDescripcion) AS servicio_nombre,
               SUM(o.OrdenMonto) AS revenue
        {DESDE} {join_s} WHERE {w}
        GROUP BY d.DivisionId, d.DivisionDescripcion, sv.ServicioId, sv.ServicioDescripcion
        ORDER BY division_nombre, revenue DESC""", p)
    evolucion = sgo.filas(f"""
        SELECT CONCAT('T', CAST(DATEPART(QUARTER, o.OrdenFecha) AS VARCHAR), '-', CAST(YEAR(o.OrdenFecha) AS VARCHAR)) AS trimestre,
               YEAR(o.OrdenFecha) AS anio, DATEPART(QUARTER, o.OrdenFecha) AS num_trimestre,
               RTRIM(sv.ServicioDescripcion) AS servicio_nombre, SUM(o.OrdenMonto) AS revenue
        {DESDE} {join_s} WHERE {w}
        GROUP BY YEAR(o.OrdenFecha), DATEPART(QUARTER, o.OrdenFecha), sv.ServicioId, sv.ServicioDescripcion
        ORDER BY anio, num_trimestre, revenue DESC""", p)

    acumulado, pareto = 0, []
    for r in servicios:
        acumulado += num(r["porcentaje_revenue"])
        pareto.append(round(acumulado, 1))
    n80 = next((i + 1 for i, v in enumerate(pareto) if v >= 80), len(pareto))
    grafico_pareto = g.columnas(etiquetas(servicios[:20]), {"% del revenue": valores(servicios[:20], "porcentaje_revenue")},
                                formato="fmt:pct")
    grafico_pareto["series"].append(g.linea("% acumulado", pareto[:20], g.SERIES[1]))
    grafico_pareto["legend"] = g.leyenda()

    top5 = [r["label"] for r in servicios[:5]]
    trimestres = list(dict.fromkeys(r["trimestre"] for r in evolucion))
    total_trim = defaultdict(float)
    por_trim = defaultdict(float)
    for r in evolucion:
        total_trim[r["trimestre"]] += num(r["revenue"])
        if r["servicio_nombre"] in top5:
            por_trim[(r["trimestre"], r["servicio_nombre"])] += num(r["revenue"])
    series_evol = {sv: [round(proporcion(por_trim[(t, sv)], total_trim[t]), 1) for t in trimestres] for sv in top5}

    divisiones = list(dict.fromkeys(str(r["division_nombre"]) for r in penetracion))
    serv_hm = [r["label"] for r in servicios[:12]]
    celdas = [[serv_hm.index(str(r["servicio_nombre"])), divisiones.index(str(r["division_nombre"])), round(num(r["revenue"]))]
              for r in penetracion if str(r["servicio_nombre"]) in serv_hm]
    principal = servicios[0] if servicios else None

    secciones = [
        seccion(
            "Curva de Pareto: servicios",
            [f"{n80} de {len(servicios)} servicios explican el 80% del revenue." if servicios else ""],
            grafico_pareto, alto=360,
            explicacion="Barras: parte del revenue de cada servicio, de mayor a menor. Línea: porcentaje acumulado. "
                        "Ambas en %, sobre el mismo eje.",
            detalle="servicio", ayuda_detalle="Hacé clic en un servicio para ver sus órdenes.",
        ),
        seccion(
            "Evolución de los 5 servicios principales (% del total)",
            [],
            g.lineas(trimestres, series_evol, formato="fmt:pct"),
            explicacion="Participación de cada uno de los 5 servicios principales en el revenue de cada trimestre.",
        ),
        seccion(
            "Perfil de los servicios principales",
            [],
            tabla=tabla("Métricas por servicio", ["Servicio", "Revenue", "% del total", "Órdenes", "Clientes",
                                                  "Ticket promedio", "Divisiones"],
                        [[r["label"], fm(r["revenue"]), pct(r["porcentaje_revenue"]), entero(r["total_ordenes"]),
                          entero(r["total_clientes"]), fm(r["ticket_promedio"]), entero(r["diversificacion_divisiones"])]
                         for r in servicios[:10]]),
            explicacion="Revenue, órdenes, clientes, ticket y en cuántas divisiones se vende cada servicio.",
        ),
        seccion(
            "Penetración: división × servicio",
            [],
            g.mapa_calor(serv_hm, divisiones, celdas), alto=max(320, 32 * len(divisiones) + 130),
            explicacion="Revenue de cada servicio (columnas) en cada división (filas). Las celdas vacías son "
                        "combinaciones sin ventas: posibles oportunidades.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total servicios", entero(len(servicios)), "con órdenes"),
            kpi("Revenue total", s.monto_corto(total(servicios, "revenue"), mon), "", AVISO_MONEDA),
            kpi("Servicio principal", principal["label"] if principal else "—",
                pct(principal["porcentaje_revenue"]) + " del revenue" if principal else ""),
            kpi("Servicios para el 80%", entero(n80), f"de {len(servicios)}"),
        ],
        "conclusiones": [
            f"{principal['label']} es el servicio principal con el {pct(principal['porcentaje_revenue'])} del revenue."
            if principal else "",
            f"{n80} servicios explican el 80% de lo facturado.",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué servicios crecen en participación?", "¿Dónde hay oportunidades de venta cruzada?"],
        "contexto_ia": {"servicios": servicios[:15], "evolucion_top5": series_evol, "trimestres": trimestres},
    }


@catalogo.detalle("portafolio")
def detalle_portafolio(clave, valor, serie, periodo, filtros):
    return respuesta_detalle(f"Órdenes · {valor}", s.COLUMNAS_ORDEN,
                             s.ordenes(filtros, "RTRIM(s.ServicioDescripcion) = %s", [valor.strip()]))


# ==========================================================================
# 6. Segmentación avanzada RFM (ord_seg)
# ==========================================================================
_SEGMENTO = """CASE
    WHEN DATEDIFF(DAY, MAX(o.OrdenFecha), GETDATE()) <= 90 AND COUNT(*) >= 5 AND SUM(o.OrdenMonto) >= 100000 THEN 'Champions'
    WHEN DATEDIFF(DAY, MAX(o.OrdenFecha), GETDATE()) <= 180 AND COUNT(*) >= 3 THEN 'Leales'
    WHEN DATEDIFF(DAY, MAX(o.OrdenFecha), GETDATE()) > 180 AND COUNT(*) >= 5 THEN 'En riesgo'
    WHEN DATEDIFF(DAY, MAX(o.OrdenFecha), GETDATE()) > 365 THEN 'Inactivos'
    WHEN COUNT(*) = 1 THEN 'Nuevos'
    ELSE 'Potenciales' END"""
_COLOR_SEGMENTO = {"Champions": g.SERIES[0], "Leales": g.SERIES[2], "Potenciales": g.SERIES[3],
                   "Nuevos": g.SERIES[6], "En riesgo": g.SERIES[1], "Inactivos": g.NEUTRO}
_RANGO_CLV = """CASE WHEN clv < 10000 THEN '< $10K' WHEN clv < 50000 THEN '$10K - $50K' WHEN clv < 100000 THEN '$50K - $100K'
    WHEN clv < 500000 THEN '$100K - $500K' ELSE '> $500K' END"""


@catalogo.registrar(
    "segmentacion", "Segmentación avanzada (RFM)",
    "Clientes según recencia, frecuencia y monto: champions, leales, en riesgo, inactivos; valor de vida y cohortes.",
    usa_periodo=False, icono="bi-gem",
    filtros=[s.F_DIVISIONES, s.F_ESTADO, s.F_SERVICIO, s.F_MONEDA, s.F_DESDE, s.F_HASTA],
)
def segmentacion(periodo, filtros):
    w, p = where(filtros)
    mon = s.moneda_principal(filtros)
    fm = _f_monto(mon)
    rfm_cliente = f"""
        SELECT p.ClienteId, RTRIM(c.ClienteNombre) AS cliente_nombre,
               DATEDIFF(DAY, MAX(o.OrdenFecha), GETDATE()) AS recency_dias, COUNT(*) AS frequency,
               SUM(o.OrdenMonto) AS monetary, {_SEGMENTO} AS segmento
        {DESDE} INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
        WHERE {w} GROUP BY p.ClienteId, c.ClienteNombre"""
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_clientes, AVG(monetary) AS clv_promedio,
               CAST(100.0 * SUM(CASE WHEN recency_dias <= 90 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS DECIMAL(10,2)) AS pct_activos_90d
        FROM ({rfm_cliente}) r""", p)
    matriz = sgo.filas(f"SELECT TOP 100 cliente_nombre, recency_dias, frequency, monetary, segmento FROM ({rfm_cliente}) r "
                       "ORDER BY monetary DESC", p)
    segmentos = sgo.filas(f"""
        SELECT segmento AS label, COUNT(*) AS cantidad_clientes, SUM(monetary) AS revenue_total, AVG(monetary) AS revenue_promedio
        FROM ({rfm_cliente}) r GROUP BY segmento ORDER BY SUM(monetary) DESC""", p)
    clv = sgo.filas(f"""
        SELECT {_RANGO_CLV} AS label, COUNT(*) AS cantidad_clientes, SUM(clv) AS revenue_total, MIN(clv) AS orden
        FROM (SELECT p.ClienteId, SUM(o.OrdenMonto) AS clv {DESDE} WHERE {w} GROUP BY p.ClienteId) x
        GROUP BY {_RANGO_CLV} ORDER BY orden""", p)
    # Cohortes: mes de la primera orden de cada cliente y cuántos volvieron a facturar en los meses siguientes
    cohortes = sgo.filas(f"""
        WITH primera AS (
            SELECT p.ClienteId, MIN(DATEFROMPARTS(YEAR(o.OrdenFecha), MONTH(o.OrdenFecha), 1)) AS cohorte
            {DESDE} WHERE {w} GROUP BY p.ClienteId),
        actividad AS (
            SELECT DISTINCT p.ClienteId, DATEFROMPARTS(YEAR(o.OrdenFecha), MONTH(o.OrdenFecha), 1) AS mes
            {DESDE} WHERE {w})
        SELECT FORMAT(pr.cohorte, 'yyyy-MM') AS cohorte, COUNT(DISTINCT pr.ClienteId) AS clientes,
               COUNT(DISTINCT CASE WHEN DATEDIFF(MONTH, pr.cohorte, a.mes) = 1 THEN pr.ClienteId END) AS mes_1,
               COUNT(DISTINCT CASE WHEN DATEDIFF(MONTH, pr.cohorte, a.mes) = 2 THEN pr.ClienteId END) AS mes_2,
               COUNT(DISTINCT CASE WHEN DATEDIFF(MONTH, pr.cohorte, a.mes) = 3 THEN pr.ClienteId END) AS mes_3,
               COUNT(DISTINCT CASE WHEN DATEDIFF(MONTH, pr.cohorte, a.mes) = 6 THEN pr.ClienteId END) AS mes_6,
               COUNT(DISTINCT CASE WHEN DATEDIFF(MONTH, pr.cohorte, a.mes) = 12 THEN pr.ClienteId END) AS mes_12
        FROM primera pr JOIN actividad a ON a.ClienteId = pr.ClienteId
        WHERE pr.cohorte >= DATEADD(MONTH, -12, DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1))
        GROUP BY pr.cohorte ORDER BY pr.cohorte""", p + p)

    nombres_seg = [n for n in _COLOR_SEGMENTO if any(m["segmento"] == n for m in matriz)]
    grafico_rfm = g.base(
        tooltip={"trigger": "item", "confine": True},
        legend=g.leyenda(),
        grid={"left": 8, "right": 24, "top": 40, "bottom": 30, "containLabel": True},
        xAxis=g.eje_valores(name="Días desde la última orden", nameLocation="middle", nameGap=28, inverse=True),
        yAxis=g.eje_valores("fmt:pesos_k", name="Monto total"),
        series=[{"name": n, "type": "scatter", "itemStyle": {"color": _COLOR_SEGMENTO[n], "opacity": .8},
                 "symbolSize": 11,
                 "data": [{"name": m["cliente_nombre"], "value": [num(m["recency_dias"]), num(m["monetary"])]}
                          for m in matriz if m["segmento"] == n]} for n in nombres_seg],
    )
    champions = next((r for r in segmentos if r["label"] == "Champions"), None)
    riesgo = next((r for r in segmentos if r["label"] == "En riesgo"), None)

    def ret(r, campo):
        return pct(proporcion(r[campo], r["clientes"])) if num(r["clientes"]) else "—"

    secciones = [
        seccion(
            "Matriz RFM: recencia vs. monto",
            ["Los más recientes y de mayor monto (arriba a la derecha) son los clientes más valiosos."],
            grafico_rfm, alto=400,
            explicacion="Cada punto es uno de los 100 clientes con más revenue. Horizontal: días desde su última orden "
                        "(el eje va de más días a menos, así lo reciente queda a la derecha). Vertical: monto total. "
                        "El color es el segmento.",
            detalle="cliente_punto", ayuda_detalle="Hacé clic en un punto para ver las órdenes del cliente.",
        ),
        seccion(
            "Distribución por segmentos",
            [f"{entero(champions['cantidad_clientes'])} clientes champions generan {fm(champions['revenue_total'])}."
             if champions else "",
             f"{entero(riesgo['cantidad_clientes'])} clientes frecuentes están en riesgo (más de 180 días sin facturar)."
             if riesgo else ""],
            g.columnas(etiquetas(segmentos), {"Clientes": valores(segmentos, "cantidad_clientes")}, rotar=0,
                       colores=[g.SERIES[0]]),
            explicacion="Champions: facturaron en los últimos 90 días, 5+ órdenes y $100K o más. Leales: últimos 180 "
                        "días y 3+ órdenes. En riesgo: 5+ órdenes pero más de 180 días sin facturar. Inactivos: más de "
                        "un año. Nuevos: una sola orden. Potenciales: el resto.",
            detalle="segmento", ayuda_detalle="Hacé clic en un segmento para ver sus clientes.",
            tabla=tabla("Segmentos", ["Segmento", "Clientes", "Revenue", "Revenue promedio"],
                        [[r["label"], entero(r["cantidad_clientes"]), fm(r["revenue_total"]), fm(r["revenue_promedio"])]
                         for r in segmentos]),
        ),
        seccion(
            "Distribución del valor de vida (CLV)",
            [lider(clv, "label", "cantidad_clientes", "clientes")],
            g.columnas(etiquetas(clv), {"Clientes": valores(clv, "cantidad_clientes")}, rotar=0),
            explicacion="Clientes agrupados por todo lo que facturaron en el período filtrado.",
        ),
        seccion(
            "Análisis de cohortes",
            ["Cada fila es el grupo de clientes que facturó por primera vez ese mes; las columnas muestran qué parte "
             "volvió a facturar 1, 2, 3, 6 y 12 meses después."],
            tabla=tabla("Retención por cohorte", ["Cohorte", "Clientes", "Mes 1", "Mes 2", "Mes 3", "Mes 6", "Mes 12"],
                        [[r["cohorte"], entero(r["clientes"]), ret(r, "mes_1"), ret(r, "mes_2"), ret(r, "mes_3"),
                          ret(r, "mes_6"), ret(r, "mes_12")] for r in cohortes]),
            explicacion="El SGO dejaba esta sección vacía; acá se calcula con los últimos 12 meses de cohortes.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total clientes", entero(k.get("total_clientes"))),
            kpi("CLV promedio", s.monto_corto(k.get("clv_promedio"), mon), "por cliente",
                "Revenue total del período ÷ clientes. " + AVISO_MONEDA),
            kpi("Activos (90 días)", pct(k.get("pct_activos_90d")), "facturaron en los últimos 90 días"),
            kpi("Champions", entero(champions["cantidad_clientes"]) if champions else "0", ""),
        ],
        "conclusiones": [
            f"{pct(k.get('pct_activos_90d'))} de los clientes facturó en los últimos 90 días.",
            f"Hay {entero(champions['cantidad_clientes'])} champions y {entero(riesgo['cantidad_clientes'])} clientes en riesgo."
            if champions and riesgo else "",
            f"El segmento que más factura es {segmentos[0]['label']} ({fm(segmentos[0]['revenue_total'])})."
            if segmentos else "",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué clientes están en riesgo?", "¿Cuántos clientes nuevos vuelven a comprar?"],
        "contexto_ia": {"kpis": k, "segmentos": segmentos, "clv": clv, "cohortes": cohortes},
    }


@catalogo.detalle("segmentacion")
def detalle_segmentacion(clave, valor, serie, periodo, filtros):
    if clave == "segmento":
        w, p = where(filtros)
        filas = sgo.filas(f"""
            SELECT TOP 500 cliente_nombre, recency_dias, frequency, monetary FROM (
                SELECT RTRIM(c.ClienteNombre) AS cliente_nombre, DATEDIFF(DAY, MAX(o.OrdenFecha), GETDATE()) AS recency_dias,
                       COUNT(*) AS frequency, SUM(o.OrdenMonto) AS monetary, {_SEGMENTO} AS segmento
                {DESDE} INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
                WHERE {w} GROUP BY p.ClienteId, c.ClienteNombre) r
            WHERE segmento = %s ORDER BY monetary DESC""", p + [valor])
        return respuesta_detalle(f"Clientes · {valor}", ["Cliente", "Días desde la última orden", "Órdenes", "Monto total"], filas)
    return respuesta_detalle(f"Órdenes de {valor}", s.COLUMNAS_ORDEN,
                             s.ordenes(filtros, "RTRIM(c.ClienteNombre) = %s", [valor.strip()]))
