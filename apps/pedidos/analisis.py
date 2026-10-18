"""
Análisis del módulo Pedidos: las 8 pantallas de analítica de pedidos del SGO
(ped_res, ped_cum, ped_dem, ped_cli, ped_rec, ped_emb, ped_efi, ped_dim) con el
mismo SQL, los mismos filtros y los registros de cada gráfico en el modal.
"""
from datetime import date

from dateutil.relativedelta import relativedelta

from apps.core import graficos as g
from apps.core import sgo
from apps.core.analisis import Catalogo, seccion
from apps.core.filtros import Filtro
from apps.core.pantalla import (
    concentracion, decimal, detalle as respuesta_detalle, dias, entero, etiquetas, extremos, kpi, lider, pct,
    proporcion, tabla, total, valores,
)
from apps.core.sgo import num

from . import services as s
from .services import FILTROS, where

catalogo = Catalogo()

MESES_TENDENCIA = Filtro.fijo("meses_tendencia", "Meses de tendencia", {"6": "6", "12": "12", "24": "24", "36": "36"}, "12")


def _desde_meses(filtros):
    return date.today() - relativedelta(months=int(filtros.get("meses_tendencia") or 12))


# ==========================================================================
# 1. Resumen general (ped_res)
# ==========================================================================
@catalogo.registrar(
    "resumen", "Resumen general",
    "Volumen, estados, cumplimiento de SLA, tiempos de cierre y clientes principales de los pedidos.",
    usa_periodo=False, icono="bi-speedometer2", filtros=FILTROS + [MESES_TENDENCIA],
)
def resumen(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_pedidos,
               COUNT(CASE WHEN {s.SIN_CIERRE} THEN 1 END) AS total_pedidos_activos,
               ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS total_vacantes_solicitadas,
               COUNT(CASE WHEN p.EstadoPedidoId = 9 THEN 1 END) AS total_finalizados,
               ROUND(CAST(COUNT(CASE WHEN p.EstadoPedidoId = 9 THEN 1 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS pct_finalizacion,
               COUNT(DISTINCT p.ClienteId) AS total_clientes_activos
        FROM dbo.Pedidos p WHERE {w}""", p)
    sla = sgo.fila(f"""
        SELECT COUNT(CASE WHEN {s.A_TIEMPO} THEN 1 END) AS cumplio_sla,
               COUNT(CASE WHEN {s.TARDE} THEN 1 END) AS no_cumplio_sla,
               COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NULL THEN 1 END) AS sin_entrega,
               ROUND(CAST(COUNT(CASE WHEN {s.A_TIEMPO} THEN 1 END) AS FLOAT)
                     / NULLIF(COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NOT NULL THEN 1 END), 0) * 100, 2) AS pct_cumplimiento
        FROM dbo.Pedidos p WHERE {w} AND p.EstadoPedidoId IN {s.CERRADOS_SLA}""", p)
    cierre = sgo.fila(f"""
        SELECT ROUND(AVG(CAST(DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre) AS FLOAT)), 2) AS avg_dias_cierre,
               MIN(DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre)) AS min_dias_cierre,
               MAX(DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre)) AS max_dias_cierre
        FROM dbo.Pedidos p
        WHERE {w} AND p.EstadoPedidoId IN {s.CERRADOS_TIEMPO} AND {s.CON_CIERRE} AND p.PedidoFecha IS NOT NULL""", p)
    # Mediana calculada en la base (el SGO traía todas las filas para calcularla en Python)
    mediana = sgo.valor(f"""
        SELECT TOP 1 PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre))
               OVER () AS median_dias_cierre
        FROM dbo.Pedidos p
        WHERE {w} AND p.EstadoPedidoId IN {s.CERRADOS_TIEMPO} AND {s.CON_CIERRE} AND p.PedidoFecha IS NOT NULL""", p)
    estados = sgo.filas(f"""
        SELECT e.EstadoPedidoDescripcion AS label, COUNT(*) AS value
        FROM dbo.Pedidos p INNER JOIN dbo.EstadosPedido e ON p.EstadoPedidoId = e.EstadoPedidoId
        WHERE {w} GROUP BY e.EstadoPedidoDescripcion ORDER BY value DESC""", p)
    divisiones = sgo.filas(f"""
        SELECT d.DivisionDescripcion AS label, COUNT(*) AS value
        FROM dbo.Pedidos p INNER JOIN dbo.Divisiones d ON p.DivisionId = d.DivisionId
        WHERE {w} GROUP BY d.DivisionDescripcion ORDER BY value DESC""", p)
    sin_entrega = sgo.fila(f"""
        SELECT COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NULL THEN 1 END) AS total_sin_entrega,
               ROUND(CAST(COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NULL THEN 1 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS pct_sin_entrega
        FROM dbo.Pedidos p WHERE {w} AND p.EstadoPedidoId IN {s.CANCELADOS}""", p)
    sin_entrega_estado = sgo.filas(f"""
        SELECT e.EstadoPedidoDescripcion AS label, COUNT(*) AS value
        FROM dbo.Pedidos p INNER JOIN dbo.EstadosPedido e ON p.EstadoPedidoId = e.EstadoPedidoId
        WHERE {w} AND p.EstadoPedidoId IN {s.CANCELADOS} AND p.PedidoFechaEntregaEfectiva IS NULL
        GROUP BY e.EstadoPedidoDescripcion ORDER BY value DESC""", p)
    tendencia = sgo.filas(f"""
        SELECT CAST(YEAR(p.PedidoFecha) AS VARCHAR(4)) + '-' + RIGHT('0' + CAST(MONTH(p.PedidoFecha) AS VARCHAR(2)), 2) AS mes,
               COUNT(*) AS total_pedidos, ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS total_vacantes
        FROM dbo.Pedidos p WHERE {w} AND p.PedidoFecha >= %s
        GROUP BY CAST(YEAR(p.PedidoFecha) AS VARCHAR(4)) + '-' + RIGHT('0' + CAST(MONTH(p.PedidoFecha) AS VARCHAR(2)), 2)
        ORDER BY mes""", p + [_desde_meses(filtros)])
    clientes = sgo.filas(f"""
        SELECT TOP 10 c.ClienteNombre AS label, COUNT(*) AS value
        FROM dbo.Pedidos p INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
        WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre ORDER BY value DESC""", p)
    # Detalle de SLA del SGO (estados 2 y 5 con fecha tope)
    sla_det = sgo.fila(f"""
        SELECT COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva <= p.PedidoFechaTopeEntrega THEN 1 END) AS a_tiempo,
               COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva > p.PedidoFechaTopeEntrega THEN 1 END) AS tarde,
               COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NULL THEN 1 END) AS sin_entrega
        FROM dbo.Pedidos p
        WHERE {w} AND p.EstadoPedidoId IN {s.SLA_DETALLE} AND p.PedidoFechaTopeEntrega IS NOT NULL""", p)

    meses_t = filtros.get("meses_tendencia") or "12"
    pares_sla = [("Cumplió SLA", num(sla_det.get("a_tiempo"))), ("No cumplió", num(sla_det.get("tarde"))),
                 ("Sin entrega", num(sla_det.get("sin_entrega")))]
    total_sla = sum(v for _, v in pares_sla)
    pico = max(tendencia, key=lambda r: num(r.get("total_pedidos")), default=None)

    secciones = [
        seccion(
            "Distribución por estado",
            [lider(estados, "label", "value", "pedidos"), concentracion(estados, "value", 3, "pedidos")],
            g.ranking(etiquetas(estados), valores(estados, "value"), "Pedidos"), alto=g.alto_ranking(len(estados)),
            explicacion="Cada barra es un estado del pedido (EstadoPedidoDescripcion) y su largo, la cantidad de "
                        "pedidos en ese estado con los filtros elegidos.",
            detalle="estado", ayuda_detalle="Hacé clic en un estado para ver sus pedidos.",
        ),
        seccion(
            f"Tendencia mensual (últimos {meses_t} meses)",
            [f"El mes con más pedidos fue {pico['mes']} con {entero(pico['total_pedidos'])} pedidos y "
             f"{entero(pico['total_vacantes'])} vacantes." if pico else ""],
            g.lineas([r["mes"] for r in tendencia], {"Pedidos": valores(tendencia, "total_pedidos"),
                                                     "Vacantes": valores(tendencia, "total_vacantes")}, area=True),
            explicacion="Pedidos ingresados por mes según PedidoFecha (línea azul) y la suma de personas pedidas "
                        "en esos pedidos (PedidoCantidadPersonas). Las dos medidas usan el mismo eje.",
        ),
        seccion(
            "Cumplimiento de SLA",
            [f"De {entero(total_sla)} pedidos con fecha tope, {pct(proporcion(pares_sla[0][1], total_sla))} se "
             f"entregó a tiempo y {pct(proporcion(pares_sla[1][1], total_sla))} tarde." if total_sla else ""],
            g.torta(pares_sla, colores=[g.ESTADO["bien"], g.ESTADO["critico"], g.NEUTRO]),
            explicacion="Pedidos con fecha tope de entrega: cumplió si la entrega efectiva fue antes o el mismo "
                        "día que la fecha tope, no cumplió si fue después, y sin entrega si todavía no tiene fecha "
                        "de entrega efectiva.",
            detalle="sla", ayuda_detalle="Hacé clic en una porción para ver esos pedidos.",
        ),
        seccion(
            "Pedidos por división",
            [lider(divisiones, "label", "value", "pedidos"), concentracion(divisiones, "value", 3, "pedidos")],
            g.ranking(etiquetas(divisiones), valores(divisiones, "value"), "Pedidos"),
            alto=g.alto_ranking(len(divisiones)),
            explicacion="Cantidad de pedidos de cada división, de mayor a menor.",
            detalle="division", ayuda_detalle="Hacé clic en una división para ver sus pedidos.",
        ),
        seccion(
            "Top 10 clientes por pedidos",
            [lider(clientes, "label", "value", "pedidos", "los 10 primeros")],
            g.ranking(etiquetas(clientes), valores(clientes, "value"), "Pedidos", g.SERIES[1]),
            alto=g.alto_ranking(len(clientes)),
            explicacion="Los 10 clientes con más pedidos en el período y filtros elegidos.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus pedidos.",
        ),
        seccion(
            "Sin entrega efectiva",
            [f"{entero(sin_entrega.get('total_sin_entrega'))} pedidos cancelados o no cubiertos no tienen fecha de "
             f"entrega efectiva ({pct(sin_entrega.get('pct_sin_entrega'))} de los cancelados y no cubiertos)."],
            g.ranking(etiquetas(sin_entrega_estado), valores(sin_entrega_estado, "value"), "Pedidos", g.NEGATIVO),
            alto=g.alto_ranking(len(sin_entrega_estado), 180),
            explicacion="Pedidos en estado Cancelado o No cubierto que nunca registraron fecha de entrega efectiva.",
            detalle="sin_entrega", ayuda_detalle="Hacé clic en un estado para ver esos pedidos.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total pedidos", entero(k.get("total_pedidos")), f"{entero(k.get('total_clientes_activos'))} clientes",
                "Todos los pedidos que cumplen con los filtros aplicados."),
            kpi("Pedidos activos", entero(k.get("total_pedidos_activos")), "sin fecha de cierre",
                "Pedidos con fecha de cierre vacía: todavía no se cerraron."),
            kpi("Cumplimiento SLA", pct(sla.get("pct_cumplimiento")),
                f"{entero(sla.get('cumplio_sla'))} a tiempo · {entero(sla.get('no_cumplio_sla'))} tardíos",
                "Cumplieron SLA ÷ total con entrega × 100. Solo pedidos Cubiertos o Finalizados: compara la entrega "
                "efectiva con la fecha tope.", alerta=num(sla.get("pct_cumplimiento")) < 80),
            kpi("Tasa de finalización", pct(k.get("pct_finalizacion")), f"{entero(k.get('total_finalizados'))} finalizados",
                "Pedidos en estado Finalizado ÷ total de pedidos × 100."),
            kpi("Vacantes solicitadas", entero(k.get("total_vacantes_solicitadas")), "",
                "Suma de la cantidad de personas de los pedidos filtrados."),
            kpi("Sin entrega efectiva", entero(sin_entrega.get("total_sin_entrega")), "cancelados + no cubiertos",
                "Pedidos Cancelados o No cubiertos sin fecha de entrega efectiva.",
                alerta=num(sin_entrega.get("total_sin_entrega")) > 0),
            kpi("Días promedio de cierre", decimal(cierre.get("avg_dias_cierre")),
                f"mediana {decimal(mediana)} días",
                "Días entre la fecha del pedido y la de cierre. Solo pedidos Cubiertos, Finalizados, Cancelados o "
                "No cubiertos con fecha de cierre válida."),
        ],
        "conclusiones": [
            f"Hay {entero(k.get('total_pedidos'))} pedidos de {entero(k.get('total_clientes_activos'))} clientes; "
            f"{entero(k.get('total_pedidos_activos'))} siguen abiertos.",
            f"El cumplimiento de SLA es {pct(sla.get('pct_cumplimiento'))} y la tasa de finalización "
            f"{pct(k.get('pct_finalizacion'))}.",
            f"Un pedido tarda en promedio {dias(cierre.get('avg_dias_cierre'))} en cerrarse (mediana "
            f"{dias(mediana)}).",
            lider(divisiones, "label", "value", "pedidos"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué división tiene peor cumplimiento?", "¿Cómo viene la tendencia de pedidos?",
                        "¿Qué clientes concentran más pedidos?"],
        "contexto_ia": {"kpis": k, "sla": sla, "cierre": cierre, "estados": estados, "divisiones": divisiones,
                        "tendencia": tendencia, "top_clientes": clientes},
    }


@catalogo.detalle("resumen")
def detalle_resumen(clave, valor, serie, periodo, filtros):
    extra, cols, condicion, params, orden = "", [], "", [], "p.PedidoFecha DESC"
    if clave == "estado":
        condicion, params = "e.EstadoPedidoDescripcion = %s", [valor]
    elif clave == "division":
        condicion, params = "d.DivisionDescripcion = %s", [valor]
    elif clave == "cliente":
        condicion, params = "c.ClienteNombre = %s", [valor]
    elif clave == "sin_entrega":
        condicion = f"p.EstadoPedidoId IN {s.CANCELADOS} AND p.PedidoFechaEntregaEfectiva IS NULL AND e.EstadoPedidoDescripcion = %s"
        params, extra, cols = [valor], s.EXTRA_TOPE, ["Tope", "Entrega"]
    elif clave == "sla":
        base = f"p.EstadoPedidoId IN {s.SLA_DETALLE} AND p.PedidoFechaTopeEntrega IS NOT NULL AND "
        condicion = base + {"Cumplió SLA": "p.PedidoFechaEntregaEfectiva <= p.PedidoFechaTopeEntrega",
                            "No cumplió": "p.PedidoFechaEntregaEfectiva > p.PedidoFechaTopeEntrega"}.get(
            valor, "p.PedidoFechaEntregaEfectiva IS NULL")
        extra, cols = s.EXTRA_TOPE, ["Tope", "Entrega"]
    filas = s.pedidos(filtros, condicion, params, extra=extra, orden=orden)
    return respuesta_detalle(f"Pedidos · {valor}", s.columnas_pedido(cols), filas)


# ==========================================================================
# 2. Cumplimiento y SLA (ped_cum)
# ==========================================================================
_RANGOS_RETRASO = """CASE
    WHEN p.PedidoFechaEntregaEfectiva <= p.PedidoFechaTopeEntrega THEN 'A tiempo'
    WHEN DATEDIFF(DAY, p.PedidoFechaTopeEntrega, p.PedidoFechaEntregaEfectiva) BETWEEN 1 AND 3 THEN '1-3 días'
    WHEN DATEDIFF(DAY, p.PedidoFechaTopeEntrega, p.PedidoFechaEntregaEfectiva) BETWEEN 4 AND 7 THEN '4-7 días'
    WHEN DATEDIFF(DAY, p.PedidoFechaTopeEntrega, p.PedidoFechaEntregaEfectiva) BETWEEN 8 AND 15 THEN '8-15 días'
    ELSE 'Más de 15 días' END"""
_ORDEN_RETRASO = ["A tiempo", "1-3 días", "4-7 días", "8-15 días", "Más de 15 días"]
_CONDICION_RETRASO = {
    "A tiempo": "p.PedidoFechaEntregaEfectiva <= p.PedidoFechaTopeEntrega",
    "1-3 días": "DATEDIFF(DAY, p.PedidoFechaTopeEntrega, p.PedidoFechaEntregaEfectiva) BETWEEN 1 AND 3",
    "4-7 días": "DATEDIFF(DAY, p.PedidoFechaTopeEntrega, p.PedidoFechaEntregaEfectiva) BETWEEN 4 AND 7",
    "8-15 días": "DATEDIFF(DAY, p.PedidoFechaTopeEntrega, p.PedidoFechaEntregaEfectiva) BETWEEN 8 AND 15",
    "Más de 15 días": "DATEDIFF(DAY, p.PedidoFechaTopeEntrega, p.PedidoFechaEntregaEfectiva) > 15",
}
_BASE_SLA = f"p.EstadoPedidoId IN {s.SLA_DETALLE} AND p.PedidoFechaTopeEntrega IS NOT NULL"


@catalogo.registrar(
    "cumplimiento", "Cumplimiento y SLA",
    "Qué parte de los pedidos se entrega antes de la fecha tope, por división, tipo y cliente, y cuánto se atrasan.",
    usa_periodo=False, icono="bi-stopwatch", filtros=FILTROS,
)
def cumplimiento(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_pedidos,
               COUNT(CASE WHEN {s.A_TIEMPO} THEN 1 END) AS cumplio_sla,
               COUNT(CASE WHEN {s.TARDE} THEN 1 END) AS no_cumplio_sla,
               COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NULL THEN 1 END) AS sin_entrega,
               ROUND(CAST(COUNT(CASE WHEN {s.A_TIEMPO} THEN 1 END) AS FLOAT)
                     / NULLIF(COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NOT NULL THEN 1 END), 0) * 100, 2) AS pct_cumplimiento,
               ROUND(AVG(CAST(CASE WHEN DATEDIFF(DAY, p.PedidoFechaTopeEntrega, p.PedidoFechaEntregaEfectiva) > 0
                     THEN DATEDIFF(DAY, p.PedidoFechaTopeEntrega, p.PedidoFechaEntregaEfectiva) ELSE 0 END AS FLOAT)), 2) AS avg_dias_retraso
        FROM dbo.Pedidos p WHERE {w} AND {_BASE_SLA}""", p)
    por_division = sgo.filas(f"""
        SELECT d.DivisionDescripcion AS label,
               COUNT(CASE WHEN {s.A_TIEMPO} THEN 1 END) AS cumplio,
               COUNT(CASE WHEN {s.TARDE} THEN 1 END) AS no_cumplio,
               ROUND(CAST(COUNT(CASE WHEN {s.A_TIEMPO} THEN 1 END) AS FLOAT)
                     / NULLIF(COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NOT NULL THEN 1 END), 0) * 100, 2) AS pct_cumplimiento
        FROM dbo.Pedidos p INNER JOIN dbo.Divisiones d ON p.DivisionId = d.DivisionId
        WHERE {w} AND {_BASE_SLA}
        GROUP BY d.DivisionDescripcion
        ORDER BY COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NOT NULL THEN 1 END) DESC""", p)
    por_tipo = sgo.filas(f"""
        SELECT tp.TipoPedidoDescripcion AS label,
               COUNT(CASE WHEN {s.A_TIEMPO} THEN 1 END) AS cumplio,
               COUNT(CASE WHEN {s.TARDE} THEN 1 END) AS no_cumplio
        FROM dbo.Pedidos p INNER JOIN dbo.TiposPedido tp ON p.TipoPedidoId = tp.TipoPedidoId
        WHERE {w} AND {_BASE_SLA}
        GROUP BY tp.TipoPedidoDescripcion
        ORDER BY COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NOT NULL THEN 1 END) DESC""", p)
    retrasos = sgo.filas(f"""
        SELECT {_RANGOS_RETRASO} AS label, COUNT(*) AS value
        FROM dbo.Pedidos p
        WHERE {w} AND {_BASE_SLA} AND p.PedidoFechaEntregaEfectiva IS NOT NULL
        GROUP BY {_RANGOS_RETRASO}""", p)
    retrasos = sorted(retrasos, key=lambda r: _ORDEN_RETRASO.index(r["label"]) if r["label"] in _ORDEN_RETRASO else 9)
    incumplidores = sgo.filas(f"""
        SELECT TOP 10 c.ClienteNombre AS label,
               COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva > p.PedidoFechaTopeEntrega THEN 1 END) AS value
        FROM dbo.Pedidos p INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
        WHERE {w} AND {_BASE_SLA} AND p.PedidoFechaEntregaEfectiva IS NOT NULL
        GROUP BY c.ClienteId, c.ClienteNombre
        HAVING COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva > p.PedidoFechaTopeEntrega THEN 1 END) > 0
        ORDER BY value DESC""", p)

    con_entrega = num(k.get("cumplio_sla")) + num(k.get("no_cumplio_sla"))
    tardios_15 = sum(num(r["value"]) for r in retrasos if r["label"] == "Más de 15 días")
    colores_retraso = [g.ESTADO["bien"], g.ESTADO["atencion"], g.ESTADO["serio"], g.NARANJA[4], g.ESTADO["critico"]]
    grafico_retrasos = g.columnas(etiquetas(retrasos), {"Pedidos": valores(retrasos, "value")}, rotar=0)
    grafico_retrasos["series"][0]["data"] = [
        {"value": num(r["value"]), "itemStyle": {"color": colores_retraso[_ORDEN_RETRASO.index(r["label"])]
                                                 if r["label"] in _ORDEN_RETRASO else g.NEUTRO}}
        for r in retrasos]

    secciones = [
        seccion(
            "Cumplimiento vs. no cumplimiento",
            [f"{pct(k.get('pct_cumplimiento'))} de los {entero(con_entrega)} pedidos entregados llegó a tiempo."],
            g.torta([("A tiempo", num(k.get("cumplio_sla"))), ("Tardío", num(k.get("no_cumplio_sla")))],
                    colores=[g.ESTADO["bien"], g.ESTADO["critico"]]),
            explicacion="Pedidos entregados con fecha tope: a tiempo si la entrega efectiva fue igual o anterior a "
                        "la fecha tope; tardío si fue posterior.",
            detalle="cumplimiento", ayuda_detalle="Hacé clic en una porción para ver esos pedidos.",
        ),
        seccion(
            "SLA por división",
            [extremos(por_division, "label", "pct_cumplimiento", pct, "mejor cumplimiento", "peor")],
            g.columnas(etiquetas(por_division), {"A tiempo": valores(por_division, "cumplio"),
                                                 "Tardío": valores(por_division, "no_cumplio")}, apiladas=True,
                       colores=[g.POSITIVO, g.NEGATIVO]),
            alto=340,
            explicacion="Cada columna es una división: la parte azul son los pedidos entregados a tiempo y la "
                        "roja los tardíos. La altura total es lo entregado.",
            detalle="division", ayuda_detalle="Hacé clic en una división para ver sus pedidos.",
            tabla=tabla("Cumplimiento por división", ["División", "A tiempo", "Tardío", "% cumplimiento"],
                        [[r["label"], entero(r["cumplio"]), entero(r["no_cumplio"]), pct(r["pct_cumplimiento"])]
                         for r in por_division]),
        ),
        seccion(
            "SLA por tipo de pedido",
            [],
            g.columnas(etiquetas(por_tipo), {"A tiempo": valores(por_tipo, "cumplio"),
                                             "Tardío": valores(por_tipo, "no_cumplio")}, apiladas=True,
                       colores=[g.POSITIVO, g.NEGATIVO]),
            explicacion="Lo mismo que por división, separado por tipo de pedido.",
            detalle="tipo", ayuda_detalle="Hacé clic en un tipo para ver sus pedidos.",
        ),
        seccion(
            "Distribución de retrasos",
            [f"{entero(tardios_15)} pedidos se entregaron con más de 15 días de atraso." if tardios_15 else "",
             f"El atraso promedio (contando los a tiempo como 0) es {dias(k.get('avg_dias_retraso'))}."],
            grafico_retrasos,
            explicacion="Pedidos entregados agrupados por días de atraso respecto de la fecha tope. Verde: a tiempo; "
                        "del amarillo al rojo, atrasos cada vez mayores.",
            detalle="retraso", ayuda_detalle="Hacé clic en un rango para ver esos pedidos.",
        ),
        seccion(
            "Top 10 clientes con más incumplimientos",
            [lider(incumplidores, "label", "value", "entregas tardías", "los 10 primeros")],
            g.ranking(etiquetas(incumplidores), valores(incumplidores, "value"), "Tardíos", g.NEGATIVO),
            alto=g.alto_ranking(len(incumplidores)),
            explicacion="Clientes con más pedidos entregados después de la fecha tope.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus pedidos.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total pedidos", entero(k.get("total_pedidos")), "con fecha tope",
                "Pedidos de los estados que usa el SGO para SLA que tienen fecha tope de entrega."),
            kpi("Cumplió SLA", entero(k.get("cumplio_sla")), "a tiempo",
                "Entrega efectiva igual o anterior a la fecha tope."),
            kpi("No cumplió SLA", entero(k.get("no_cumplio_sla")), "tardíos",
                "Entrega efectiva posterior a la fecha tope.", alerta=num(k.get("no_cumplio_sla")) > 0),
            kpi("% cumplimiento", pct(k.get("pct_cumplimiento")), f"{entero(k.get('sin_entrega'))} sin entrega",
                "A tiempo ÷ pedidos con entrega × 100.", alerta=num(k.get("pct_cumplimiento")) < 80),
            kpi("Promedio de retraso", dias(k.get("avg_dias_retraso")), "",
                "Días de atraso promedio; los entregados a tiempo cuentan como 0."),
        ],
        "conclusiones": [
            f"El cumplimiento de SLA es {pct(k.get('pct_cumplimiento'))}: {entero(k.get('cumplio_sla'))} a tiempo y "
            f"{entero(k.get('no_cumplio_sla'))} tardíos.",
            extremos(por_division, "label", "pct_cumplimiento", pct, "mejor cumplimiento por división", "peor"),
            lider(incumplidores, "label", "value", "entregas tardías", "los 10 clientes con más atrasos"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Por qué baja el cumplimiento?", "¿Qué clientes se atrasan más?"],
        "contexto_ia": {"kpis": k, "por_division": por_division, "por_tipo": por_tipo, "retrasos": retrasos,
                        "incumplidores": incumplidores},
    }


@catalogo.detalle("cumplimiento")
def detalle_cumplimiento(clave, valor, serie, periodo, filtros):
    condicion, params = f"{_BASE_SLA} AND p.PedidoFechaEntregaEfectiva IS NOT NULL", []
    extra, cols = s.EXTRA_TOPE, ["Tope", "Entrega"]
    orden = "p.PedidoFecha DESC"
    if clave == "cumplimiento":
        condicion += " AND " + ("p.PedidoFechaEntregaEfectiva <= p.PedidoFechaTopeEntrega" if valor == "A tiempo"
                                else "p.PedidoFechaEntregaEfectiva > p.PedidoFechaTopeEntrega")
        extra, cols = s.EXTRA_DIFERENCIA, ["Tope", "Entrega", "Días de diferencia"]
        orden = "ABS(DATEDIFF(DAY, p.PedidoFechaTopeEntrega, p.PedidoFechaEntregaEfectiva)) DESC"
    elif clave == "retraso":
        condicion += " AND " + _CONDICION_RETRASO.get(valor, "1=0")
        extra, cols = s.EXTRA_DIFERENCIA, ["Tope", "Entrega", "Días de diferencia"]
        orden = "ABS(DATEDIFF(DAY, p.PedidoFechaTopeEntrega, p.PedidoFechaEntregaEfectiva)) DESC"
    elif clave == "division":
        condicion += " AND d.DivisionDescripcion = %s"
        params = [valor]
    elif clave == "tipo":
        condicion += " AND tp.TipoPedidoDescripcion = %s"
        params = [valor]
    elif clave == "cliente":
        condicion += " AND c.ClienteNombre = %s"
        params = [valor]
    if serie in ("A tiempo", "Tardío") and clave in ("division", "tipo"):
        condicion += " AND " + ("p.PedidoFechaEntregaEfectiva <= p.PedidoFechaTopeEntrega" if serie == "A tiempo"
                                else "p.PedidoFechaEntregaEfectiva > p.PedidoFechaTopeEntrega")
    joins = "INNER JOIN dbo.TiposPedido tp ON p.TipoPedidoId = tp.TipoPedidoId" if clave == "tipo" else ""
    filas = s.pedidos(filtros, condicion, params, extra=extra, joins=joins, orden=orden)
    titulo = f"Pedidos · {valor}" + (f" · {serie}" if serie in ("A tiempo", "Tardío") else "")
    return respuesta_detalle(titulo, s.columnas_pedido(cols), filas)


# ==========================================================================
# 3. Demanda y planificación (ped_dem)
# ==========================================================================
_RANGO_VACANTES = """CASE
    WHEN p.PedidoCantidadPersonas = 1 THEN '1 persona'
    WHEN p.PedidoCantidadPersonas BETWEEN 2 AND 3 THEN '2-3 personas'
    WHEN p.PedidoCantidadPersonas BETWEEN 4 AND 5 THEN '4-5 personas'
    WHEN p.PedidoCantidadPersonas BETWEEN 6 AND 10 THEN '6-10 personas'
    ELSE 'Más de 10' END"""
_CONDICION_VACANTES = {
    "1 persona": "p.PedidoCantidadPersonas = 1",
    "2-3 personas": "p.PedidoCantidadPersonas BETWEEN 2 AND 3",
    "4-5 personas": "p.PedidoCantidadPersonas BETWEEN 4 AND 5",
    "6-10 personas": "p.PedidoCantidadPersonas BETWEEN 6 AND 10",
    "Más de 10": "p.PedidoCantidadPersonas > 10",
}
_DIAS = {1: "Domingo", 2: "Lunes", 3: "Martes", 4: "Miércoles", 5: "Jueves", 6: "Viernes", 7: "Sábado"}


@catalogo.registrar(
    "demanda", "Demanda y planificación",
    "Cuántos pedidos y vacantes llegan, cuándo, de qué divisiones, tipos y clientes, y de qué tamaño.",
    usa_periodo=False, icono="bi-graph-up-arrow", filtros=FILTROS + [MESES_TENDENCIA],
)
def demanda(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_pedidos,
               ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS total_vacantes_solicitadas,
               COUNT(CASE WHEN {s.SIN_CIERRE} THEN 1 END) AS pedidos_activos,
               ISNULL(SUM(CASE WHEN {s.SIN_CIERRE} THEN p.PedidoCantidadPersonas ELSE 0 END), 0) AS vacantes_activas,
               ROUND(CAST(COUNT(*) AS FLOAT) / NULLIF(DATEDIFF(MONTH, MIN(p.PedidoFecha), MAX(p.PedidoFecha)) + 1, 0), 2) AS avg_pedidos_mes
        FROM dbo.Pedidos p WHERE {w}""", p)
    tendencia = sgo.filas(f"""
        SELECT CAST(YEAR(p.PedidoFecha) AS VARCHAR(4)) + '-' + RIGHT('0' + CAST(MONTH(p.PedidoFecha) AS VARCHAR(2)), 2) AS mes,
               COUNT(*) AS total_pedidos, ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS total_vacantes
        FROM dbo.Pedidos p WHERE {w} AND p.PedidoFecha >= %s
        GROUP BY CAST(YEAR(p.PedidoFecha) AS VARCHAR(4)) + '-' + RIGHT('0' + CAST(MONTH(p.PedidoFecha) AS VARCHAR(2)), 2)
        ORDER BY mes""", p + [_desde_meses(filtros)])
    por_division = sgo.filas(f"""
        SELECT d.DivisionDescripcion AS label, COUNT(*) AS total_pedidos, ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS total_vacantes
        FROM dbo.Pedidos p INNER JOIN dbo.Divisiones d ON p.DivisionId = d.DivisionId
        WHERE {w} GROUP BY d.DivisionDescripcion ORDER BY total_pedidos DESC""", p)
    por_tipo = sgo.filas(f"""
        SELECT tp.TipoPedidoDescripcion AS label, COUNT(*) AS total_pedidos, ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS total_vacantes
        FROM dbo.Pedidos p INNER JOIN dbo.TiposPedido tp ON p.TipoPedidoId = tp.TipoPedidoId
        WHERE {w} GROUP BY tp.TipoPedidoDescripcion ORDER BY total_pedidos DESC""", p)
    semana = sgo.filas(f"""
        SELECT DATEPART(WEEKDAY, p.PedidoFecha) AS dia_orden, COUNT(*) AS value
        FROM dbo.Pedidos p WHERE {w} GROUP BY DATEPART(WEEKDAY, p.PedidoFecha) ORDER BY dia_orden""", p)
    clientes = sgo.filas(f"""
        SELECT TOP 10 c.ClienteNombre AS label, COUNT(*) AS total_pedidos, ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS total_vacantes
        FROM dbo.Pedidos p INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
        WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre ORDER BY total_pedidos DESC""", p)
    tamanos = sgo.filas(f"""
        SELECT {_RANGO_VACANTES} AS label, COUNT(*) AS value
        FROM dbo.Pedidos p WHERE {w} AND p.PedidoCantidadPersonas > 0
        GROUP BY {_RANGO_VACANTES} ORDER BY MIN(p.PedidoCantidadPersonas)""", p)

    dias_semana = [_DIAS.get(int(num(r["dia_orden"])), str(r["dia_orden"])) if str(r["dia_orden"]).isdigit()
                   or isinstance(r["dia_orden"], (int, float)) else str(r["dia_orden"]) for r in semana]
    dia_pico = max(zip(dias_semana, semana), key=lambda x: num(x[1]["value"]), default=None)
    meses_t = filtros.get("meses_tendencia") or "12"
    secciones = [
        seccion(
            f"Tendencia mensual (últimos {meses_t} meses)",
            [f"Promedio histórico: {decimal(k.get('avg_pedidos_mes'))} pedidos por mes."],
            g.lineas([r["mes"] for r in tendencia], {"Pedidos": valores(tendencia, "total_pedidos"),
                                                     "Vacantes": valores(tendencia, "total_vacantes")}, area=True),
            explicacion="Pedidos ingresados por mes (PedidoFecha) y vacantes pedidas en esos pedidos.",
        ),
        seccion(
            "Demanda por división",
            [lider(por_division, "label", "total_pedidos", "pedidos")],
            g.columnas(etiquetas(por_division), {"Pedidos": valores(por_division, "total_pedidos"),
                                                 "Vacantes": valores(por_division, "total_vacantes")}),
            alto=340,
            explicacion="Por división: pedidos (azul) y vacantes pedidas (naranja), lado a lado.",
            detalle="division", ayuda_detalle="Hacé clic en una división para ver sus pedidos.",
        ),
        seccion(
            "Demanda por tipo de pedido",
            [lider(por_tipo, "label", "total_pedidos", "pedidos")],
            g.columnas(etiquetas(por_tipo), {"Pedidos": valores(por_tipo, "total_pedidos"),
                                             "Vacantes": valores(por_tipo, "total_vacantes")}),
            explicacion="Pedidos y vacantes por tipo de pedido.",
            detalle="tipo", ayuda_detalle="Hacé clic en un tipo para ver sus pedidos.",
        ),
        seccion(
            "Distribución por día de la semana",
            [f"El día con más pedidos es el {dia_pico[0].lower()} ({entero(dia_pico[1]['value'])})." if dia_pico else ""],
            g.columnas(dias_semana, {"Pedidos": valores(semana, "value")}, rotar=0),
            explicacion="Día de la semana en que se cargó cada pedido (según PedidoFecha).",
        ),
        seccion(
            "Top 10 clientes por volumen",
            [lider(clientes, "label", "total_pedidos", "pedidos", "los 10 primeros")],
            g.ranking(etiquetas(clientes), valores(clientes, "total_pedidos"), "Pedidos"),
            alto=g.alto_ranking(len(clientes)),
            explicacion="Los 10 clientes con más pedidos.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus pedidos.",
            tabla=tabla("Pedidos y vacantes por cliente", ["Cliente", "Pedidos", "Vacantes"],
                        [[r["label"], entero(r["total_pedidos"]), entero(r["total_vacantes"])] for r in clientes]),
        ),
        seccion(
            "Vacantes por pedido",
            [lider(tamanos, "label", "value", "pedidos")],
            g.columnas(etiquetas(tamanos), {"Pedidos": valores(tamanos, "value")}, rotar=0),
            explicacion="Cuántos pedidos piden 1 persona, 2-3, 4-5, 6-10 o más de 10.",
            detalle="tamano", ayuda_detalle="Hacé clic en un rango para ver esos pedidos.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total pedidos", entero(k.get("total_pedidos")), "", "Pedidos con los filtros aplicados."),
            kpi("Vacantes solicitadas", entero(k.get("total_vacantes_solicitadas")), "",
                "Suma de PedidoCantidadPersonas."),
            kpi("Pedidos activos", entero(k.get("pedidos_activos")), "sin cierre", "Pedidos sin fecha de cierre."),
            kpi("Vacantes activas", entero(k.get("vacantes_activas")), "", "Personas pedidas en pedidos sin cierre."),
            kpi("Promedio pedidos/mes", decimal(k.get("avg_pedidos_mes")), "",
                "Pedidos ÷ meses entre el primer y el último pedido del filtro."),
        ],
        "conclusiones": [
            f"Llegaron {entero(k.get('total_pedidos'))} pedidos por {entero(k.get('total_vacantes_solicitadas'))} "
            f"vacantes; {entero(k.get('vacantes_activas'))} vacantes siguen abiertas.",
            lider(por_division, "label", "total_pedidos", "pedidos"),
            lider(tamanos, "label", "value", "pedidos"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué meses tienen más demanda?", "¿Qué divisiones piden más vacantes?"],
        "contexto_ia": {"kpis": k, "tendencia": tendencia, "por_division": por_division, "por_tipo": por_tipo,
                        "clientes": clientes, "tamanos": tamanos},
    }


@catalogo.detalle("demanda")
def detalle_demanda(clave, valor, serie, periodo, filtros):
    condicion, params, joins, orden = "", [valor], "", "p.PedidoFecha DESC"
    if clave == "division":
        condicion = "d.DivisionDescripcion = %s"
    elif clave == "tipo":
        condicion, joins = "tp.TipoPedidoDescripcion = %s", "INNER JOIN dbo.TiposPedido tp ON p.TipoPedidoId = tp.TipoPedidoId"
    elif clave == "cliente":
        condicion = "c.ClienteNombre = %s"
    elif clave == "tamano":
        condicion, params = _CONDICION_VACANTES.get(valor, "1=0"), []
        orden = "p.PedidoCantidadPersonas DESC, p.PedidoFecha DESC"
    filas = s.pedidos(filtros, condicion, params, joins=joins, orden=orden)
    return respuesta_detalle(f"Pedidos · {valor}", s.columnas_pedido(), filas)


# ==========================================================================
# 4. Análisis por cliente (ped_cli)
# ==========================================================================
_RECURRENCIA = """CASE
    WHEN cantidad_pedidos = 1 THEN '1 pedido'
    WHEN cantidad_pedidos BETWEEN 2 AND 5 THEN '2-5 pedidos'
    WHEN cantidad_pedidos BETWEEN 6 AND 10 THEN '6-10 pedidos'
    WHEN cantidad_pedidos BETWEEN 11 AND 20 THEN '11-20 pedidos'
    ELSE 'Más de 20' END"""
_CONDICION_RECURRENCIA = {"1 pedido": "COUNT(*) = 1", "2-5 pedidos": "COUNT(*) BETWEEN 2 AND 5",
                          "6-10 pedidos": "COUNT(*) BETWEEN 6 AND 10", "11-20 pedidos": "COUNT(*) BETWEEN 11 AND 20",
                          "Más de 20": "COUNT(*) > 20"}
_ESTADOS_GRUPO = {"Finalizados": "p.EstadoPedidoId = 9", "Activos": f"p.EstadoPedidoId IN {s.ACTIVOS}",
                  "Cancelados": f"p.EstadoPedidoId IN {s.CANCELADOS}"}


@catalogo.registrar(
    "clientes", "Análisis por cliente",
    "Qué clientes piden más, cómo terminan sus pedidos, cuántas vacantes les quedan pendientes y cuán recurrentes son.",
    usa_periodo=False, icono="bi-buildings",
    filtros=FILTROS + [Filtro.numero("min_pedidos", "Mínimo de pedidos (recurrentes)", 10)],
)
def clientes(periodo, filtros):
    w, p = where(filtros)
    minimo = max(1, int(filtros.get("min_pedidos") or 10))
    k = sgo.fila(f"""
        SELECT COUNT(DISTINCT p.ClienteId) AS total_clientes, COUNT(*) AS total_pedidos,
               ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS total_vacantes,
               ROUND(CAST(COUNT(*) AS FLOAT) / NULLIF(COUNT(DISTINCT p.ClienteId), 0), 2) AS avg_pedidos_por_cliente,
               ROUND(CAST(ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS FLOAT) / NULLIF(COUNT(DISTINCT p.ClienteId), 0), 2) AS avg_vacantes_por_cliente
        FROM dbo.Pedidos p WHERE {w}""", p)
    top = sgo.filas(f"""
        SELECT TOP 10 c.ClienteNombre AS label, COUNT(*) AS total_pedidos, ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS total_vacantes
        FROM dbo.Pedidos p INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
        WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre ORDER BY total_pedidos DESC""", p)
    estados = sgo.filas(f"""
        SELECT TOP 10 c.ClienteNombre AS label,
               SUM(CASE WHEN p.EstadoPedidoId = 9 THEN 1 ELSE 0 END) AS finalizados,
               SUM(CASE WHEN p.EstadoPedidoId IN {s.ACTIVOS} THEN 1 ELSE 0 END) AS activos,
               SUM(CASE WHEN p.EstadoPedidoId IN {s.CANCELADOS} THEN 1 ELSE 0 END) AS cancelados
        FROM dbo.Pedidos p INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
        WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre ORDER BY COUNT(*) DESC""", p)
    pendientes = sgo.filas(f"""
        SELECT TOP 10 c.ClienteNombre AS label,
               ISNULL(SUM(CASE WHEN {s.SIN_CIERRE} THEN p.PedidoCantidadPersonas ELSE 0 END), 0) AS vacantes_pendientes
        FROM dbo.Pedidos p INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
        WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre
        HAVING ISNULL(SUM(CASE WHEN {s.SIN_CIERRE} THEN p.PedidoCantidadPersonas ELSE 0 END), 0) > 0
        ORDER BY vacantes_pendientes DESC""", p)
    recurrencia = sgo.filas(f"""
        SELECT {_RECURRENCIA} AS label, COUNT(*) AS value, MIN(cantidad_pedidos) AS orden
        FROM (SELECT p.ClienteId, COUNT(*) AS cantidad_pedidos FROM dbo.Pedidos p WHERE {w} GROUP BY p.ClienteId) AS cp
        GROUP BY {_RECURRENCIA} ORDER BY orden""", p)
    recurrentes = sgo.filas(f"""
        SELECT c.ClienteNombre AS cliente, COUNT(*) AS total_pedidos, ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS total_vacantes,
               SUM(CASE WHEN p.EstadoPedidoId = 9 THEN 1 ELSE 0 END) AS finalizados,
               SUM(CASE WHEN p.EstadoPedidoId IN {s.ACTIVOS} THEN 1 ELSE 0 END) AS activos,
               SUM(CASE WHEN p.EstadoPedidoId IN {s.CANCELADOS} THEN 1 ELSE 0 END) AS cancelados
        FROM dbo.Pedidos p INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
        WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre HAVING COUNT(*) >= %s
        ORDER BY total_pedidos DESC""", p + [minimo])

    una_vez = next((num(r["value"]) for r in recurrencia if r["label"] == "1 pedido"), 0)
    secciones = [
        seccion(
            "Top 10 clientes por volumen",
            [lider(top, "label", "total_pedidos", "pedidos", "los 10 primeros"),
             concentracion(top, "total_pedidos", 3, "pedidos del top 10")],
            g.ranking(etiquetas(top), valores(top, "total_pedidos"), "Pedidos"), alto=g.alto_ranking(len(top)),
            explicacion="Los 10 clientes con más pedidos.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus pedidos.",
        ),
        seccion(
            "Distribución de estados por cliente",
            [],
            g.columnas(etiquetas(estados), {"Finalizados": valores(estados, "finalizados"),
                                            "Activos": valores(estados, "activos"),
                                            "Cancelados": valores(estados, "cancelados")}, apiladas=True,
                       colores=[g.SERIES[0], g.SERIES[3], g.NEGATIVO]),
            alto=360,
            explicacion="Para los 10 clientes con más pedidos: cuántos están finalizados, activos (abierto, en "
                        "proceso, suspendido o cubierto) y cancelados (cancelado o no cubierto).",
            detalle="estado_cliente", ayuda_detalle="Hacé clic en un tramo para ver esos pedidos del cliente.",
        ),
        seccion(
            "Vacantes pendientes por cliente",
            [lider(pendientes, "label", "vacantes_pendientes", "vacantes pendientes", "los 10 primeros")],
            g.ranking(etiquetas(pendientes), valores(pendientes, "vacantes_pendientes"), "Vacantes", g.SERIES[1]),
            alto=g.alto_ranking(len(pendientes)),
            explicacion="Personas pedidas en pedidos que todavía no tienen fecha de cierre.",
            detalle="pendientes", ayuda_detalle="Hacé clic en un cliente para ver sus pedidos abiertos.",
        ),
        seccion(
            "Recurrencia de clientes",
            [f"{entero(una_vez)} clientes hicieron un solo pedido." if una_vez else "",
             lider(recurrencia, "label", "value", "clientes")],
            g.columnas(etiquetas(recurrencia), {"Clientes": valores(recurrencia, "value")}, rotar=0),
            explicacion="Clientes agrupados según cuántos pedidos hicieron con los filtros elegidos.",
            detalle="recurrencia", ayuda_detalle="Hacé clic en un rango para ver los clientes.",
        ),
        seccion(
            f"Clientes recurrentes ({minimo}+ pedidos)",
            [f"{entero(len(recurrentes))} clientes tienen {minimo} pedidos o más."],
            tabla=tabla(f"Clientes con {minimo} pedidos o más",
                        ["Cliente", "Pedidos", "Vacantes", "Finalizados", "Activos", "Cancelados"],
                        [[r["cliente"], entero(r["total_pedidos"]), entero(r["total_vacantes"]), entero(r["finalizados"]),
                          entero(r["activos"]), entero(r["cancelados"])] for r in recurrentes]),
            explicacion="El mínimo de pedidos se cambia en los filtros.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total clientes", entero(k.get("total_clientes")), "con pedidos", "Clientes distintos con pedidos."),
            kpi("Total pedidos", entero(k.get("total_pedidos"))),
            kpi("Total vacantes", entero(k.get("total_vacantes"))),
            kpi("Pedidos por cliente", decimal(k.get("avg_pedidos_por_cliente")), "promedio"),
            kpi("Vacantes por cliente", decimal(k.get("avg_vacantes_por_cliente")), "promedio"),
        ],
        "conclusiones": [
            f"{entero(k.get('total_clientes'))} clientes hicieron {entero(k.get('total_pedidos'))} pedidos "
            f"({decimal(k.get('avg_pedidos_por_cliente'))} por cliente).",
            lider(top, "label", "total_pedidos", "pedidos", "los 10 primeros"),
            lider(pendientes, "label", "vacantes_pendientes", "vacantes pendientes", "los 10 con más pendientes"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué clientes tienen más vacantes pendientes?", "¿Cuántos clientes piden una sola vez?"],
        "contexto_ia": {"kpis": k, "top": top, "estados": estados, "pendientes": pendientes, "recurrencia": recurrencia},
    }


@catalogo.detalle("clientes")
def detalle_clientes(clave, valor, serie, periodo, filtros):
    if clave == "recurrencia":
        w, p = where(filtros)
        filas = sgo.filas(f"""
            SELECT TOP 500 c.ClienteNombre AS cliente, COUNT(*) AS total_pedidos,
                   ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS total_vacantes,
                   CONVERT(VARCHAR(10), MIN(p.PedidoFecha), 103) AS primer_pedido,
                   CONVERT(VARCHAR(10), MAX(p.PedidoFecha), 103) AS ultimo_pedido
            FROM dbo.Pedidos p INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId
            WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre
            HAVING {_CONDICION_RECURRENCIA.get(valor, "1=0")}
            ORDER BY total_pedidos DESC""", p)
        return respuesta_detalle(f"Clientes · {valor}",
                                 ["Cliente", "Pedidos", "Vacantes", "Primer pedido", "Último pedido"], filas)
    condicion = "c.ClienteNombre = %s"
    if clave == "estado_cliente" and serie in _ESTADOS_GRUPO:
        condicion += " AND " + _ESTADOS_GRUPO[serie]
    if clave == "pendientes":
        condicion += f" AND {s.SIN_CIERRE}"
    filas = s.pedidos(filtros, condicion, [valor])
    sufijo = f" · {serie}" if clave == "estado_cliente" else (" · abiertos" if clave == "pendientes" else "")
    return respuesta_detalle(f"Pedidos de {valor}{sufijo}", s.columnas_pedido(), filas)


# ==========================================================================
# 5. Reclutamiento y perfiles (ped_rec)
# ==========================================================================
@catalogo.registrar(
    "reclutamiento", "Reclutamiento y perfiles",
    "Quiénes se asignaron a los pedidos: perfiles, género, educación, edad, estados de asignación y ejecutivos.",
    usa_periodo=False, icono="bi-person-badge", filtros=FILTROS,
)
def reclutamiento(periodo, filtros):
    w, p = where(filtros)
    base = f"FROM dbo.Pedidos p INNER JOIN ({{asig}}) asig ON p.PedidoId = asig.PedidoId"
    k = sgo.fila(f"""
        SELECT COUNT(DISTINCT asig.CandidatoId) AS total_candidatos_asignados, COUNT(*) AS total_asignaciones,
               ROUND(AVG(CAST(CASE WHEN asig.AsignacionFechaIngreso >= p.PedidoFecha
                     THEN DATEDIFF(DAY, p.PedidoFecha, asig.AsignacionFechaIngreso) END AS FLOAT)), 2) AS avg_dias_reclutamiento,
               COUNT(DISTINCT CASE WHEN asig.AsignacionFechaEgreso IS NOT NULL THEN asig.CandidatoId END) AS candidatos_con_egreso
        {base.format(asig=s.asignaciones_validas("fechas"))} WHERE {w}""", p)
    cobertura = sgo.fila(f"""
        SELECT SUM(p.PedidoCantidadPersonas) AS total_vacantes_solicitadas,
               COUNT(DISTINCT CHECKSUM(asig.PedidoId, asig.CandidatoId)) AS total_asignaciones_unicas,
               ROUND(CAST(COUNT(DISTINCT CHECKSUM(asig.PedidoId, asig.CandidatoId)) AS FLOAT)
                     / NULLIF(SUM(p.PedidoCantidadPersonas), 0) * 100, 2) AS tasa_cobertura
        FROM dbo.Pedidos p LEFT JOIN ({s.asignaciones_validas()}) asig ON p.PedidoId = asig.PedidoId
        WHERE {w} AND p.EstadoPedidoId IN {s.CERRADOS_SLA}""", p)
    perfiles = sgo.filas(f"""
        SELECT TOP 10 RTRIM(pc.PerfilCandidatoDescripcion) AS label, COUNT(DISTINCT asig.CandidatoId) AS total_candidatos,
               COUNT(*) AS total_asignaciones
        {base.format(asig=s.asignaciones_validas())}
        INNER JOIN dbo.Candidatos c ON asig.CandidatoId = c.CandidatoId
        INNER JOIN dbo.PerfilesCandidatos pc ON c.PerfilCandidatoId = pc.PerfilCandidatoId
        WHERE {w} GROUP BY pc.PerfilCandidatoDescripcion ORDER BY total_asignaciones DESC""", p)
    genero = sgo.filas(f"""
        SELECT CASE c.CandidatoSexo WHEN 'M' THEN 'Masculino' WHEN 'F' THEN 'Femenino' ELSE 'No especificado' END AS label,
               COUNT(DISTINCT asig.CandidatoId) AS value
        {base.format(asig=s.asignaciones_validas())}
        INNER JOIN dbo.Candidatos c ON asig.CandidatoId = c.CandidatoId
        WHERE {w} GROUP BY c.CandidatoSexo ORDER BY value DESC""", p)
    educacion = sgo.filas(f"""
        SELECT ISNULL(RTRIM(ne.NivelEducativoDescripcion), 'Sin especificar') AS label, COUNT(DISTINCT asig.CandidatoId) AS value
        {base.format(asig=s.asignaciones_validas())}
        INNER JOIN dbo.Candidatos c ON asig.CandidatoId = c.CandidatoId
        LEFT JOIN dbo.NivelesEducativos ne ON c.NivelEducativoId = ne.NivelEducativoId
        WHERE {w} GROUP BY ne.NivelEducativoDescripcion ORDER BY value DESC""", p)
    rango_edad = """CASE
        WHEN DATEDIFF(YEAR, c.CandidatoFechaNacimiento, GETDATE()) < 25 THEN 'Menos de 25'
        WHEN DATEDIFF(YEAR, c.CandidatoFechaNacimiento, GETDATE()) BETWEEN 25 AND 34 THEN '25-34 años'
        WHEN DATEDIFF(YEAR, c.CandidatoFechaNacimiento, GETDATE()) BETWEEN 35 AND 44 THEN '35-44 años'
        WHEN DATEDIFF(YEAR, c.CandidatoFechaNacimiento, GETDATE()) BETWEEN 45 AND 54 THEN '45-54 años'
        ELSE '55 o más' END"""
    edades = sgo.filas(f"""
        SELECT {rango_edad} AS label, COUNT(DISTINCT asig.CandidatoId) AS value
        {base.format(asig=s.asignaciones_validas())}
        INNER JOIN dbo.Candidatos c ON asig.CandidatoId = c.CandidatoId
        WHERE {w} AND c.CandidatoFechaNacimiento IS NOT NULL AND c.CandidatoFechaNacimiento NOT IN {s.FECHAS_NULAS}
        GROUP BY {rango_edad} ORDER BY MIN(DATEDIFF(YEAR, c.CandidatoFechaNacimiento, GETDATE()))""", p)
    estados = sgo.filas(f"""
        SELECT ISNULL(RTRIM(ea.EstadoAsignacionDescripcion), 'Asignado (postulante)') AS label, COUNT(*) AS value
        {base.format(asig=s.asignaciones_validas("estado"))}
        LEFT JOIN dbo.EstadosAsignacion ea ON asig.EstadoAsignacionId = ea.EstadoAsignacionId
        WHERE {w} GROUP BY ea.EstadoAsignacionDescripcion ORDER BY value DESC""", p)
    ejecutivos = sgo.filas(f"""
        SELECT TOP 10 ISNULL(RTRIM(ec.EjecutivoCuentaNombre) + ' ' + RTRIM(ec.EjecutivoCuentaApellido), 'Sin ejecutivo') AS label,
               COUNT(DISTINCT asig.CandidatoId) AS candidatos_asignados, COUNT(*) AS total_asignaciones
        {base.format(asig=s.asignaciones_validas("ejecutivo"))}
        LEFT JOIN dbo.EjecutivosCuenta ec ON asig.AsignacionEjecutivoId = ec.EjecutivoCuentaId
        WHERE {w} GROUP BY ec.EjecutivoCuentaId, ec.EjecutivoCuentaNombre, ec.EjecutivoCuentaApellido
        ORDER BY total_asignaciones DESC""", p)

    secciones = [
        seccion(
            "Top 10 perfiles más demandados",
            [lider(perfiles, "label", "total_asignaciones", "asignaciones", "los 10 primeros")],
            g.ranking(etiquetas(perfiles), valores(perfiles, "total_asignaciones"), "Asignaciones"),
            alto=g.alto_ranking(len(perfiles)),
            explicacion="Perfil del candidato (PerfilesCandidatos) de las personas asignadas a los pedidos.",
        ),
        seccion(
            "Distribución por género",
            [lider(genero, "label", "value", "candidatos")],
            g.torta([(r["label"], num(r["value"])) for r in genero]),
            explicacion="Candidatos distintos asignados, según el sexo registrado.",
        ),
        seccion(
            "Candidatos por nivel educativo",
            [lider(educacion, "label", "value", "candidatos")],
            g.ranking(etiquetas(educacion), valores(educacion, "value"), "Candidatos", g.SERIES[2]),
            alto=g.alto_ranking(len(educacion)),
            explicacion="Nivel educativo registrado de los candidatos asignados.",
        ),
        seccion(
            "Distribución por rango de edad",
            [lider(edades, "label", "value", "candidatos")],
            g.columnas(etiquetas(edades), {"Candidatos": valores(edades, "value")}, rotar=0),
            explicacion="Edad actual de los candidatos asignados (según su fecha de nacimiento).",
        ),
        seccion(
            "Estados de las asignaciones",
            [lider(estados, "label", "value", "asignaciones")],
            g.ranking(etiquetas(estados), valores(estados, "value"), "Asignaciones", g.SERIES[3]),
            alto=g.alto_ranking(len(estados), 200),
            explicacion="Estado de cada asignación. Las que vienen de postulantes con evento de asignación no "
                        "tienen estado y aparecen como «Asignado (postulante)».",
        ),
        seccion(
            "Top 10 ejecutivos por asignaciones",
            [lider(ejecutivos, "label", "total_asignaciones", "asignaciones", "los 10 primeros")],
            g.ranking(etiquetas(ejecutivos), valores(ejecutivos, "total_asignaciones"), "Asignaciones", g.SERIES[1]),
            alto=g.alto_ranking(len(ejecutivos)),
            explicacion="Ejecutivo de cuenta que registró la asignación.",
        ),
    ]
    return {
        "kpis": [
            kpi("Candidatos asignados", entero(k.get("total_candidatos_asignados")), "distintos",
                "Asignaciones con ingreso no rechazadas más postulantes con evento de asignación, sin duplicar."),
            kpi("Total asignaciones", entero(k.get("total_asignaciones"))),
            kpi("Tasa de cobertura", pct(cobertura.get("tasa_cobertura")), "pedidos cubiertos y finalizados",
                "Asignaciones únicas ÷ vacantes pedidas × 100, solo en pedidos Cubiertos o Finalizados."),
            kpi("Días de reclutamiento", decimal(k.get("avg_dias_reclutamiento")), "promedio",
                "Días entre la fecha del pedido y el ingreso del candidato."),
            kpi("Candidatos con egreso", entero(k.get("candidatos_con_egreso")), "",
                "Candidatos asignados que ya tienen fecha de egreso."),
        ],
        "conclusiones": [
            f"Se asignaron {entero(k.get('total_candidatos_asignados'))} candidatos en "
            f"{entero(k.get('total_asignaciones'))} asignaciones, con una cobertura de {pct(cobertura.get('tasa_cobertura'))}.",
            f"Desde que entra el pedido hasta el ingreso pasan en promedio {dias(k.get('avg_dias_reclutamiento'))}.",
            lider(perfiles, "label", "total_asignaciones", "asignaciones", "los 10 perfiles principales"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué perfiles se piden más?", "¿Cuánto tarda en promedio el reclutamiento?"],
        "contexto_ia": {"kpis": k, "cobertura": cobertura, "perfiles": perfiles, "genero": genero,
                        "educacion": educacion, "edades": edades, "estados": estados, "ejecutivos": ejecutivos},
    }


# ==========================================================================
# 6. Embudo y estados (ped_emb)
# ==========================================================================
_ORDEN_EMBUDO = "CASE ep.EstadoPedidoId WHEN 7 THEN 1 WHEN 2 THEN 2 WHEN 4 THEN 3 WHEN 8 THEN 4 WHEN 9 THEN 5 " \
                "WHEN 3 THEN 6 WHEN 6 THEN 7 WHEN 5 THEN 8 WHEN 1 THEN 9 ELSE 10 END"
_ATASCADO = f"p.EstadoPedidoId IN {s.ABIERTOS_ZOMBIE} AND (p.PedidoFechaCierre IS NULL OR " \
            "p.PedidoFechaCierre = CAST('1900-01-01' AS DATETIME)) AND DATEDIFF(DAY, p.PedidoFecha, GETDATE()) > %s"
_ZOMBIE = f"p.EstadoPedidoId IN {s.ABIERTOS_ZOMBIE} AND (p.PedidoFechaCierre IS NULL OR " \
          "p.PedidoFechaCierre = CAST('1900-01-01' AS DATETIME)) AND p.PedidoFechaEntregaEfectiva IS NULL " \
          "AND DATEDIFF(DAY, p.PedidoFecha, GETDATE()) > 30"


@catalogo.registrar(
    "embudo", "Embudo y estados",
    "Por qué estados pasan los pedidos, cuánto tardan, cuáles están atascados y cuántos se derivan o traspasan.",
    usa_periodo=False, icono="bi-funnel",
    filtros=FILTROS + [Filtro.numero("dias_atascados", "Días para considerar atascado", 15)],
)
def embudo(periodo, filtros):
    w, p = where(filtros)
    dias_limite = max(1, int(filtros.get("dias_atascados") or 15))
    total_pedidos = num(sgo.valor(f"SELECT COUNT(*) AS total FROM dbo.Pedidos p WHERE {w}", p))
    conversion = sgo.filas(f"""
        SELECT ep.EstadoPedidoDescripcion AS label, ep.EstadoPedidoId AS estado_id, COUNT(*) AS value
        FROM dbo.Pedidos p INNER JOIN dbo.EstadosPedido ep ON p.EstadoPedidoId = ep.EstadoPedidoId
        WHERE {w} GROUP BY ep.EstadoPedidoDescripcion, ep.EstadoPedidoId ORDER BY {_ORDEN_EMBUDO}""", p)
    tiempos = sgo.filas(f"""
        SELECT ep.EstadoPedidoDescripcion AS label,
               ROUND(AVG(CAST(DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre) AS FLOAT)), 2) AS avg_dias_cierre,
               ROUND(AVG(CAST(DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaEntregaEfectiva) AS FLOAT)), 2) AS avg_dias_primera_entrega
        FROM dbo.Pedidos p INNER JOIN dbo.EstadosPedido ep ON p.EstadoPedidoId = ep.EstadoPedidoId
        WHERE {w} AND p.EstadoPedidoId IN {s.CERRADOS_TIEMPO}
          AND (p.PedidoFechaCierre IS NOT NULL OR p.PedidoFechaEntregaEfectiva IS NOT NULL)
        GROUP BY ep.EstadoPedidoDescripcion ORDER BY avg_dias_cierre DESC""", p)
    der = sgo.fila(f"""
        SELECT COUNT(CASE WHEN p.PedidoDerivado = 'S' THEN 1 END) AS total_derivados,
               COUNT(CASE WHEN p.PedidoTraspaso = 'S' THEN 1 END) AS total_traspasos,
               ROUND(CAST(COUNT(CASE WHEN p.PedidoDerivado = 'S' THEN 1 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS pct_derivados,
               ROUND(CAST(COUNT(CASE WHEN p.PedidoTraspaso = 'S' THEN 1 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS pct_traspasos
        FROM dbo.Pedidos p WHERE {w} AND p.EstadoPedidoId IN {s.ACTIVOS}""", p)
    der_division = sgo.filas(f"""
        SELECT d.DivisionDescripcion AS label,
               COUNT(CASE WHEN p.PedidoDerivado = 'S' THEN 1 END) AS derivados,
               COUNT(CASE WHEN p.PedidoTraspaso = 'S' THEN 1 END) AS traspasos
        FROM dbo.Pedidos p INNER JOIN dbo.Divisiones d ON p.DivisionId = d.DivisionId
        WHERE {w} AND p.EstadoPedidoId IN {s.ACTIVOS}
        GROUP BY d.DivisionDescripcion
        HAVING COUNT(CASE WHEN p.PedidoDerivado = 'S' THEN 1 END) > 0 OR COUNT(CASE WHEN p.PedidoTraspaso = 'S' THEN 1 END) > 0
        ORDER BY COUNT(CASE WHEN p.PedidoDerivado = 'S' THEN 1 END) + COUNT(CASE WHEN p.PedidoTraspaso = 'S' THEN 1 END) DESC""", p)
    distribucion = sgo.filas(f"""
        SELECT ep.EstadoPedidoDescripcion AS label, COUNT(*) AS cantidad,
               ROUND(AVG(CAST(DATEDIFF(DAY, p.PedidoFecha, ISNULL(p.PedidoFechaCierre, GETDATE())) AS FLOAT)), 2) AS avg_dias_en_estado,
               ROUND(CAST(COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NOT NULL THEN 1 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS pct_con_entrega
        FROM dbo.Pedidos p INNER JOIN dbo.EstadosPedido ep ON p.EstadoPedidoId = ep.EstadoPedidoId
        WHERE {w} GROUP BY ep.EstadoPedidoDescripcion ORDER BY cantidad DESC""", p)
    atascados = sgo.filas(f"""
        SELECT ep.EstadoPedidoDescripcion AS label, COUNT(*) AS value
        FROM dbo.Pedidos p INNER JOIN dbo.EstadosPedido ep ON p.EstadoPedidoId = ep.EstadoPedidoId
        WHERE {w} AND {_ATASCADO} GROUP BY ep.EstadoPedidoDescripcion ORDER BY value DESC""", p + [dias_limite])
    sin_entrega = sgo.fila(f"""
        SELECT COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NULL THEN 1 END) AS total_sin_entrega,
               ROUND(CAST(COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NULL THEN 1 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS pct_sin_entrega
        FROM dbo.Pedidos p WHERE {w} AND p.EstadoPedidoId IN {s.CANCELADOS}""", p)
    zombie = num(sgo.valor(f"SELECT COUNT(*) AS total_zombie FROM dbo.Pedidos p WHERE {w} AND {_ZOMBIE}", p))

    total_atascados = total(atascados, "value")
    secciones = [
        seccion(
            "Embudo de conversión por estado",
            [f"{pct(proporcion(r['value'], total_pedidos))} de los pedidos está en «{r['label']}»."
             for r in sorted(conversion, key=lambda r: -num(r["value"]))[:2]],
            g.embudo([(r["label"], num(r["value"])) for r in conversion]), alto=380,
            explicacion="Pedidos en cada estado, en el orden del flujo normal (abierto → en proceso → suspendido → "
                        "cubierto → finalizado) y al final los cancelados y no cubiertos.",
            detalle="estado", ayuda_detalle="Hacé clic en un estado para ver sus pedidos.",
        ),
        seccion(
            "Tiempo promedio por estado",
            [extremos(tiempos, "label", "avg_dias_cierre", dias, "más lento", "más rápido")],
            g.columnas(etiquetas(tiempos), {"Días hasta el cierre": valores(tiempos, "avg_dias_cierre"),
                                            "Días hasta la primera entrega": valores(tiempos, "avg_dias_primera_entrega")}),
            explicacion="Para los pedidos que terminaron (cubiertos, finalizados, cancelados o no cubiertos): días "
                        "promedio desde la fecha del pedido hasta el cierre y hasta la entrega efectiva.",
        ),
        seccion(
            "Distribución detallada por estado",
            [],
            tabla=tabla("Pedidos por estado", ["Estado", "Pedidos", "Días promedio en el estado", "% con entrega"],
                        [[r["label"], entero(r["cantidad"]), decimal(r["avg_dias_en_estado"]), pct(r["pct_con_entrega"])]
                         for r in distribucion]),
            explicacion="Días en el estado: desde la fecha del pedido hasta el cierre, o hasta hoy si sigue abierto.",
        ),
        seccion(
            f"Pedidos atascados (más de {dias_limite} días abiertos)",
            [f"{entero(total_atascados)} pedidos llevan más de {dias_limite} días sin cerrarse."
             if total_atascados else "No hay pedidos atascados con este criterio."],
            g.ranking(etiquetas(atascados), valores(atascados, "value"), "Pedidos", g.NEGATIVO),
            alto=g.alto_ranking(len(atascados), 200),
            explicacion="Pedidos abiertos (sin fecha de cierre) creados hace más días que el límite elegido en los "
                        "filtros, por estado.",
            detalle="atascado", ayuda_detalle="Hacé clic en un estado para ver los pedidos atascados.",
        ),
        seccion(
            "Derivados y traspasos por división",
            [f"{entero(der.get('total_derivados'))} pedidos activos derivados ({pct(der.get('pct_derivados'))}) y "
             f"{entero(der.get('total_traspasos'))} traspasados ({pct(der.get('pct_traspasos'))})."],
            g.columnas(etiquetas(der_division), {"Derivados": valores(der_division, "derivados"),
                                                 "Traspasos": valores(der_division, "traspasos")}),
            explicacion="Pedidos activos marcados como derivados (PedidoDerivado = 'S') o traspasados "
                        "(PedidoTraspaso = 'S'), por división.",
            detalle="derivado", ayuda_detalle="Hacé clic en una barra para ver esos pedidos.",
        ),
    ]
    return {
        "kpis": [
            kpi("Pedidos atascados", entero(total_atascados), f"más de {dias_limite} días",
                "Pedidos abiertos creados hace más días que el límite.", alerta=total_atascados > 0),
            kpi("Sin entrega", entero(sin_entrega.get("total_sin_entrega")), pct(sin_entrega.get("pct_sin_entrega")),
                "Cancelados o no cubiertos sin fecha de entrega efectiva."),
            kpi("Derivados", entero(der.get("total_derivados")), pct(der.get("pct_derivados")),
                "Pedidos activos con PedidoDerivado = 'S'."),
            kpi("Traspasos", entero(der.get("total_traspasos")), pct(der.get("pct_traspasos")),
                "Pedidos activos con PedidoTraspaso = 'S'."),
            kpi("Zombie (30 días)", entero(zombie), "sin entrega ni cierre",
                "Pedidos abiertos hace más de 30 días, sin entrega efectiva y sin cierre.", alerta=zombie > 0),
        ],
        "conclusiones": [
            f"{entero(total_atascados)} pedidos llevan más de {dias_limite} días abiertos y {entero(zombie)} superan los "
            f"30 días sin entrega.",
            extremos(tiempos, "label", "avg_dias_cierre", dias, "estado más lento en cerrar", "más rápido"),
            f"{pct(der.get('pct_derivados'))} de los pedidos activos se derivó y {pct(der.get('pct_traspasos'))} se traspasó.",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Dónde se atascan los pedidos?", "¿Qué divisiones derivan más?"],
        "contexto_ia": {"conversion": conversion, "tiempos": tiempos, "derivados": der, "atascados": atascados,
                        "zombie": zombie, "sin_entrega": sin_entrega},
    }


@catalogo.detalle("embudo")
def detalle_embudo(clave, valor, serie, periodo, filtros):
    if clave == "estado":
        condicion, params = "e.EstadoPedidoDescripcion = %s", [valor]
    elif clave == "atascado":
        dias_limite = max(1, int(filtros.get("dias_atascados") or 15))
        condicion, params = f"{_ATASCADO} AND e.EstadoPedidoDescripcion = %s", [dias_limite, valor]
    else:  # derivado / traspaso por división
        campo = "p.PedidoTraspaso" if serie == "Traspasos" else "p.PedidoDerivado"
        condicion, params = f"p.EstadoPedidoId IN {s.ACTIVOS} AND {campo} = 'S' AND d.DivisionDescripcion = %s", [valor]
    filas = s.pedidos(filtros, condicion, params)
    return respuesta_detalle(f"Pedidos · {valor}" + (f" · {serie}" if clave == "derivado" else ""),
                             s.columnas_pedido(), filas)


# ==========================================================================
# 7. Operaciones y eficiencia (ped_efi)
# ==========================================================================
_DIAS_CIERRE = f"CASE WHEN {s.CON_CIERRE} THEN DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre) END"
_RANGO_CIERRE = """CASE
    WHEN DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre) <= 7 THEN '0-7 días'
    WHEN DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre) BETWEEN 8 AND 15 THEN '8-15 días'
    WHEN DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre) BETWEEN 16 AND 30 THEN '16-30 días'
    WHEN DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre) BETWEEN 31 AND 60 THEN '31-60 días'
    ELSE 'Más de 60 días' END"""
_CONDICION_CIERRE = {
    "0-7 días": "DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre) <= 7",
    "8-15 días": "DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre) BETWEEN 8 AND 15",
    "16-30 días": "DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre) BETWEEN 16 AND 30",
    "31-60 días": "DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre) BETWEEN 31 AND 60",
    "Más de 60 días": "DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre) > 60",
}


@catalogo.registrar(
    "eficiencia", "Operaciones y eficiencia",
    "Cuánto tardan los pedidos en cerrarse y entregarse, qué parte termina o se cancela, y dónde se pierden.",
    usa_periodo=False, icono="bi-gear", filtros=FILTROS,
)
def eficiencia(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT ROUND(AVG(CAST({_DIAS_CIERRE} AS FLOAT)), 2) AS avg_dias_cierre,
               ROUND(AVG(CAST(CASE WHEN p.PedidoFechaEntregaEfectiva IS NOT NULL AND p.PedidoFechaEntregaEfectiva >= p.PedidoFecha
                     THEN DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaEntregaEfectiva) END AS FLOAT)), 2) AS avg_dias_entrega,
               ROUND(CAST(COUNT(CASE WHEN p.EstadoPedidoId = 9 THEN 1 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS tasa_finalizacion,
               ROUND(CAST(COUNT(CASE WHEN p.EstadoPedidoId IN {s.CANCELADOS} THEN 1 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS tasa_cancelacion,
               ROUND(CAST(ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS FLOAT) / NULLIF(COUNT(*), 0), 2) AS avg_vacantes_por_pedido,
               COUNT(CASE WHEN DATEDIFF(DAY, p.PedidoFecha, GETDATE()) > 30 AND {s.SIN_CIERRE} THEN 1 END) AS pedidos_zombie
        FROM dbo.Pedidos p WHERE {w}""", p)
    por_division = sgo.filas(f"""
        SELECT d.DivisionDescripcion AS label, ROUND(AVG(CAST({_DIAS_CIERRE} AS FLOAT)), 2) AS avg_dias_cierre,
               ROUND(CAST(COUNT(CASE WHEN p.EstadoPedidoId = 9 THEN 1 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS pct_finalizacion
        FROM dbo.Pedidos p INNER JOIN dbo.Divisiones d ON p.DivisionId = d.DivisionId
        WHERE {w} GROUP BY d.DivisionDescripcion ORDER BY avg_dias_cierre ASC""", p)
    por_tipo = sgo.filas(f"""
        SELECT tp.TipoPedidoDescripcion AS label, COUNT(*) AS total_pedidos, ROUND(AVG(CAST({_DIAS_CIERRE} AS FLOAT)), 2) AS avg_dias_cierre
        FROM dbo.Pedidos p INNER JOIN dbo.TiposPedido tp ON p.TipoPedidoId = tp.TipoPedidoId
        WHERE {w} GROUP BY tp.TipoPedidoDescripcion ORDER BY total_pedidos DESC""", p)
    emb = sgo.fila(f"""
        SELECT COUNT(*) AS total_pedidos, COUNT(CASE WHEN p.EstadoPedidoId NOT IN {s.CANCELADOS} THEN 1 END) AS no_cancelados,
               COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NOT NULL THEN 1 END) AS con_entrega,
               COUNT(CASE WHEN p.EstadoPedidoId = 9 THEN 1 END) AS finalizados
        FROM dbo.Pedidos p WHERE {w}""", p)
    tiempos = sgo.filas(f"""
        SELECT {_RANGO_CIERRE} AS label, COUNT(*) AS value
        FROM dbo.Pedidos p WHERE {w} AND {s.CON_CIERRE}
        GROUP BY {_RANGO_CIERRE} ORDER BY MIN(DATEDIFF(DAY, p.PedidoFecha, p.PedidoFechaCierre))""", p)
    activos = sgo.filas(f"""
        SELECT e.EstadoPedidoDescripcion AS label, COUNT(*) AS value
        FROM dbo.Pedidos p INNER JOIN dbo.EstadosPedido e ON p.EstadoPedidoId = e.EstadoPedidoId
        WHERE {w} AND {s.SIN_CIERRE} GROUP BY e.EstadoPedidoDescripcion ORDER BY value DESC""", p)

    pasos = [("Total pedidos", num(emb.get("total_pedidos"))), ("No cancelados", num(emb.get("no_cancelados"))),
             ("Con entrega", num(emb.get("con_entrega"))), ("Finalizados", num(emb.get("finalizados")))]
    secciones = [
        seccion(
            "Eficiencia por división: días de cierre",
            [extremos(por_division, "label", "avg_dias_cierre", dias, "más lento", "más rápido")],
            g.ranking(etiquetas(por_division), valores(por_division, "avg_dias_cierre"), "Días promedio"),
            alto=g.alto_ranking(len(por_division)),
            explicacion="Días promedio entre la fecha del pedido y la de cierre, por división. Menos es mejor.",
            detalle="division", ayuda_detalle="Hacé clic en una división para ver sus pedidos.",
        ),
        seccion(
            "Eficiencia por división: tasa de finalización",
            [extremos(por_division, "label", "pct_finalizacion", pct, "más alta", "más baja")],
            g.ranking(etiquetas(sorted(por_division, key=lambda r: -num(r["pct_finalizacion"]))),
                      valores(sorted(por_division, key=lambda r: -num(r["pct_finalizacion"])), "pct_finalizacion"),
                      "% finalizados", g.SERIES[2], formato="fmt:pct"),
            alto=g.alto_ranking(len(por_division)),
            explicacion="Porcentaje de pedidos de cada división que llegaron a Finalizado.",
            detalle="division", ayuda_detalle="Hacé clic en una división para ver sus pedidos.",
        ),
        seccion(
            "Embudo de conversión",
            [f"De {entero(pasos[0][1])} pedidos, {pct(proporcion(pasos[2][1], pasos[0][1]))} tuvo entrega y "
             f"{pct(proporcion(pasos[3][1], pasos[0][1]))} se finalizó." if pasos[0][1] else ""],
            g.embudo(pasos), alto=320,
            explicacion="Cuántos pedidos quedan en cada paso: todos, los no cancelados, los que tuvieron entrega "
                        "efectiva y los finalizados.",
        ),
        seccion(
            "Distribución de tiempos de cierre",
            [lider(tiempos, "label", "value", "pedidos")],
            g.columnas(etiquetas(tiempos), {"Pedidos": valores(tiempos, "value")}, rotar=0),
            explicacion="Pedidos cerrados agrupados por los días que tardaron en cerrarse.",
            detalle="tiempo", ayuda_detalle="Hacé clic en un rango para ver esos pedidos.",
        ),
        seccion(
            "Productividad por tipo de pedido",
            [],
            g.ranking(etiquetas(por_tipo), valores(por_tipo, "avg_dias_cierre"), "Días promedio de cierre", g.SERIES[1]),
            alto=g.alto_ranking(len(por_tipo), 200),
            explicacion="Días promedio de cierre por tipo de pedido.",
            tabla=tabla("Por tipo de pedido", ["Tipo", "Pedidos", "Días promedio de cierre"],
                        [[r["label"], entero(r["total_pedidos"]), decimal(r["avg_dias_cierre"])] for r in por_tipo]),
        ),
        seccion(
            "Estados de los pedidos activos",
            [lider(activos, "label", "value", "pedidos abiertos")],
            g.ranking(etiquetas(activos), valores(activos, "value"), "Pedidos", g.SERIES[3]),
            alto=g.alto_ranking(len(activos), 200),
            explicacion="Pedidos sin fecha de cierre, por estado.",
            detalle="activo", ayuda_detalle="Hacé clic en un estado para ver los pedidos abiertos.",
        ),
    ]
    return {
        "kpis": [
            kpi("Días promedio de cierre", decimal(k.get("avg_dias_cierre")), "", "Desde la fecha del pedido hasta el cierre."),
            kpi("Días promedio de entrega", decimal(k.get("avg_dias_entrega")), "",
                "Desde la fecha del pedido hasta la entrega efectiva."),
            kpi("Tasa de finalización", pct(k.get("tasa_finalizacion")), "", "Pedidos Finalizados ÷ total × 100."),
            kpi("Tasa de cancelación", pct(k.get("tasa_cancelacion")), "", "Cancelados y no cubiertos ÷ total × 100.",
                alerta=num(k.get("tasa_cancelacion")) > 20),
            kpi("Vacantes por pedido", decimal(k.get("avg_vacantes_por_pedido")), "promedio"),
            kpi("Pedidos zombie (30 días)", entero(k.get("pedidos_zombie")), "abiertos hace +30 días",
                "Pedidos sin cierre creados hace más de 30 días.", alerta=num(k.get("pedidos_zombie")) > 0),
        ],
        "conclusiones": [
            f"Un pedido tarda {dias(k.get('avg_dias_cierre'))} en cerrarse y {dias(k.get('avg_dias_entrega'))} en "
            f"entregarse, en promedio.",
            f"Se finaliza el {pct(k.get('tasa_finalizacion'))} y se cancela el {pct(k.get('tasa_cancelacion'))} de los pedidos.",
            extremos(por_division, "label", "avg_dias_cierre", dias, "división más lenta", "más rápida"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué división cierra más rápido?", "¿Cuántos pedidos están sin movimiento?"],
        "contexto_ia": {"kpis": k, "por_division": por_division, "por_tipo": por_tipo, "embudo": emb,
                        "tiempos": tiempos, "activos": activos},
    }


@catalogo.detalle("eficiencia")
def detalle_eficiencia(clave, valor, serie, periodo, filtros):
    params = [valor]
    if clave == "division":
        condicion = "d.DivisionDescripcion = %s"
    elif clave == "activo":
        condicion = f"{s.SIN_CIERRE} AND e.EstadoPedidoDescripcion = %s"
    else:  # tiempo
        condicion, params = f"{s.CON_CIERRE} AND {_CONDICION_CIERRE.get(valor, '1=0')}", []
    filas = s.pedidos(filtros, condicion, params)
    return respuesta_detalle(f"Pedidos · {valor}", s.columnas_pedido(), filas)


# ==========================================================================
# 8. Dimensiones estratégicas (ped_dim)
# ==========================================================================
_PCT_FIN = "ROUND(CAST(COUNT(CASE WHEN p.EstadoPedidoId = 9 THEN 1 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2)"


@catalogo.registrar(
    "dimensiones", "Dimensiones estratégicas",
    "Pedidos por marca, línea, practice area y centro de costo, eficiencia por división y concentración del volumen.",
    usa_periodo=False, icono="bi-diagram-3", filtros=FILTROS,
)
def dimensiones(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(DISTINCT p.MarcaId) AS total_marcas, COUNT(DISTINCT p.LineaId) AS total_lineas,
               COUNT(DISTINCT p.PracticeAreaId) AS total_practice_areas, COUNT(DISTINCT p.CentroCostoId) AS total_centros_costo,
               COUNT(*) AS total_pedidos, {_PCT_FIN} AS tasa_finalizacion
        FROM dbo.Pedidos p WHERE {w}""", p)

    def por(tabla_sql, id_col, desc_col, sin, top=True):
        return sgo.filas(f"""
            SELECT {'TOP 10 ' if top else ''}ISNULL(x.{desc_col}, '{sin}') AS label, COUNT(*) AS total_pedidos,
                   ISNULL(SUM(p.PedidoCantidadPersonas), 0) AS total_vacantes, {_PCT_FIN} AS pct_finalizacion,
                   ROUND(AVG(CAST({_DIAS_CIERRE} AS FLOAT)), 2) AS avg_dias_cierre
            FROM dbo.Pedidos p LEFT JOIN dbo.{tabla_sql} x ON p.{id_col} = x.{id_col}
            WHERE {w} GROUP BY x.{id_col}, x.{desc_col} ORDER BY total_pedidos DESC""", p)

    marcas = por("Marcas", "MarcaId", "MarcaDescripcion", "Sin marca")
    lineas = por("Lineas", "LineaId", "LineaDescripcion", "Sin línea")
    practice = por("PracticeAreas", "PracticeAreaId", "PracticeAreaDescripcion", "Sin practice area", top=False)
    centros = por("CentrosCosto", "CentroCostoId", "CentroCostoDescripcion", "Sin centro de costo")
    division = sgo.filas(f"""
        SELECT d.DivisionDescripcion AS label, COUNT(*) AS total_pedidos, {_PCT_FIN} AS pct_finalizacion,
               ROUND(CAST(COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NOT NULL AND p.PedidoFechaEntregaEfectiva >= p.PedidoFecha
                     AND p.PedidoFechaEntregaEfectiva <= p.PedidoFechaTopeEntrega THEN 1 END) AS FLOAT)
                     / NULLIF(COUNT(CASE WHEN p.PedidoFechaEntregaEfectiva IS NOT NULL AND p.EstadoPedidoId IN {s.CERRADOS_SLA} THEN 1 END), 0) * 100, 2) AS pct_sla,
               ROUND(AVG(CAST({_DIAS_CIERRE} AS FLOAT)), 2) AS avg_dias_cierre
        FROM dbo.Pedidos p INNER JOIN dbo.Divisiones d ON p.DivisionId = d.DivisionId
        WHERE {w} GROUP BY d.DivisionId, d.DivisionDescripcion ORDER BY total_pedidos DESC""", p)

    total_div = total(division, "total_pedidos")
    concentracion_div = sorted(({"label": r["label"], "pct": proporcion(r["total_pedidos"], total_div)} for r in division),
                               key=lambda r: -r["pct"])

    def bloque(titulo, filas, campo_titulo, clave, color):
        return seccion(
            titulo, [lider(filas, "label", "total_pedidos", "pedidos"),
                     extremos(filas, "label", "pct_finalizacion", pct, "mayor finalización", "menor")],
            g.ranking(etiquetas(filas), valores(filas, "total_pedidos"), "Pedidos", color),
            alto=g.alto_ranking(len(filas)),
            explicacion=f"Pedidos por {campo_titulo}. En la tabla, vacantes y porcentaje de pedidos finalizados.",
            detalle=clave, ayuda_detalle=f"Hacé clic en una barra para ver los pedidos de esa {campo_titulo}.",
            tabla=tabla(f"Por {campo_titulo}", [campo_titulo.capitalize(), "Pedidos", "Vacantes", "% finalizados"],
                        [[r["label"], entero(r["total_pedidos"]), entero(r["total_vacantes"]), pct(r["pct_finalizacion"])]
                         for r in filas]),
        )

    secciones = [
        bloque("Top 10 marcas por volumen", marcas, "marca", "marca", g.SERIES[0]),
        bloque("Top 10 líneas por volumen", lineas, "línea", "linea", g.SERIES[1]),
        seccion(
            "Performance por practice area",
            [lider(practice, "label", "total_pedidos", "pedidos")],
            g.ranking(etiquetas(practice), valores(practice, "total_pedidos"), "Pedidos", g.SERIES[2]),
            alto=g.alto_ranking(len(practice)),
            explicacion="Pedidos por practice area; en la tabla, finalización y días promedio de cierre.",
            detalle="practice", ayuda_detalle="Hacé clic en una practice area para ver sus pedidos.",
            tabla=tabla("Por practice area", ["Practice area", "Pedidos", "% finalizados", "Días de cierre"],
                        [[r["label"], entero(r["total_pedidos"]), pct(r["pct_finalizacion"]), decimal(r["avg_dias_cierre"])]
                         for r in practice]),
        ),
        bloque("Top 10 centros de costo", centros, "centro de costo", "centro", g.SERIES[3]),
        seccion(
            "Eficiencia por división",
            [extremos(division, "label", "pct_finalizacion", pct, "mayor finalización", "menor"),
             extremos(division, "label", "pct_sla", pct, "mejor SLA", "peor")],
            g.columnas(etiquetas(division), {"% finalización": valores(division, "pct_finalizacion"),
                                             "% SLA": valores(division, "pct_sla")}, formato="fmt:pct"),
            alto=340,
            explicacion="Las tres métricas de eficiencia de cada división: % de pedidos finalizados y % de entregas "
                        "a tiempo (en el gráfico, mismo eje en %) y días promedio de cierre (en la tabla).",
            detalle="division", ayuda_detalle="Hacé clic en una división para ver sus pedidos.",
            tabla=tabla("Eficiencia por división", ["División", "Pedidos", "% finalizados", "% SLA", "Días de cierre"],
                        [[r["label"], entero(r["total_pedidos"]), pct(r["pct_finalizacion"]), pct(r["pct_sla"]),
                          decimal(r["avg_dias_cierre"])] for r in division]),
        ),
        seccion(
            "Concentración de riesgo por división",
            [f"{concentracion_div[0]['label']} concentra el {pct(concentracion_div[0]['pct'])} de los pedidos."
             if concentracion_div else ""],
            g.ranking([r["label"] for r in concentracion_div], [round(r["pct"], 1) for r in concentracion_div],
                      "% de los pedidos", g.NEGATIVO, formato="fmt:pct"),
            alto=g.alto_ranking(len(concentracion_div)),
            explicacion="Qué parte del total de pedidos depende de cada división. Una división con mucho peso es "
                        "un riesgo si su demanda cae.",
            detalle="division", ayuda_detalle="Hacé clic en una división para ver sus pedidos.",
        ),
    ]
    return {
        "kpis": [
            kpi("Marcas activas", entero(k.get("total_marcas"))),
            kpi("Líneas activas", entero(k.get("total_lineas"))),
            kpi("Practice areas", entero(k.get("total_practice_areas"))),
            kpi("Centros de costo", entero(k.get("total_centros_costo"))),
            kpi("Tasa de finalización", pct(k.get("tasa_finalizacion")), f"{entero(k.get('total_pedidos'))} pedidos"),
        ],
        "conclusiones": [
            lider(marcas, "label", "total_pedidos", "pedidos", "las 10 marcas principales"),
            f"{concentracion_div[0]['label']} concentra el {pct(concentracion_div[0]['pct'])} de los pedidos."
            if concentracion_div else "",
            extremos(division, "label", "pct_sla", pct, "mejor SLA por división", "peor"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué marcas tienen menor finalización?", "¿Dependemos mucho de una división?"],
        "contexto_ia": {"kpis": k, "marcas": marcas, "lineas": lineas, "practice": practice, "centros": centros,
                        "division": division},
    }


_DIMENSION = {
    "marca": ("LEFT JOIN dbo.Marcas x ON p.MarcaId = x.MarcaId", "ISNULL(x.MarcaDescripcion, 'Sin marca')"),
    "linea": ("LEFT JOIN dbo.Lineas x ON p.LineaId = x.LineaId", "ISNULL(x.LineaDescripcion, 'Sin línea')"),
    "practice": ("LEFT JOIN dbo.PracticeAreas x ON p.PracticeAreaId = x.PracticeAreaId",
                 "ISNULL(x.PracticeAreaDescripcion, 'Sin practice area')"),
    "centro": ("LEFT JOIN dbo.CentrosCosto x ON p.CentroCostoId = x.CentroCostoId",
               "ISNULL(x.CentroCostoDescripcion, 'Sin centro de costo')"),
}


@catalogo.detalle("dimensiones")
def detalle_dimensiones(clave, valor, serie, periodo, filtros):
    if clave in _DIMENSION:
        joins, expresion = _DIMENSION[clave]
        filas = s.pedidos(filtros, f"{expresion} = %s", [valor], joins=joins)
    else:
        filas = s.pedidos(filtros, "d.DivisionDescripcion = %s", [valor])
    return respuesta_detalle(f"Pedidos · {valor}", s.columnas_pedido(), filas)
