"""
Análisis del módulo Viáticos: las 5 pantallas de viáticos del SGO (via_res,
via_tem, via_txt, via_ano, via_cli) con el mismo SQL y filtros, y los viáticos
de cada gráfico en el modal.
"""
from collections import defaultdict
from datetime import date

from apps.core import graficos as g
from apps.core import sgo
from apps.core.analisis import Catalogo, seccion
from apps.core.pantalla import (
    concentracion, decimal, detalle as respuesta_detalle, entero, etiquetas, extremos, kpi, lider, pct,
    proporcion, tabla, total, valores,
)
from apps.core.sgo import num

from . import services as s
from .services import DESDE, FECHA, FECHA_VALIDA, IMPORTE, OBS, monto, monto_corto, where

catalogo = Catalogo()

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
         "Noviembre", "Diciembre"]
DIAS = {1: "Domingo", 2: "Lunes", 3: "Martes", 4: "Miércoles", 5: "Jueves", 6: "Viernes", 7: "Sábado"}
JOIN_CLI = "INNER JOIN dbo.Clientes c ON p.ClienteId = c.ClienteId"
JOIN_CAND = "INNER JOIN dbo.Candidatos cand ON a.CandidatoId = cand.CandidatoId"
CANDIDATO = "RTRIM(cand.CandidatoNombre) + ' ' + RTRIM(cand.CandidatoApellido)"


def _ym(r):
    """'2026-03' a partir de las columnas anio y mes."""
    try:
        return f"{int(num(r['anio'], None))}-{int(num(r['mes'], None)):02d}"
    except (TypeError, ValueError):
        return str(r.get("mes"))


# ==========================================================================
# 1. Resumen general (via_res)
# ==========================================================================
_RANGOS_IMPORTE = [("$0 - $500", f"{IMPORTE} < 500"), ("$500 - $1.000", f"{IMPORTE} >= 500 AND {IMPORTE} < 1000"),
                   ("$1.000 - $2.000", f"{IMPORTE} >= 1000 AND {IMPORTE} < 2000"),
                   ("$2.000 - $5.000", f"{IMPORTE} >= 2000 AND {IMPORTE} < 5000"), ("$5.000 o más", f"{IMPORTE} >= 5000")]


@catalogo.registrar(
    "resumen", "Resumen general",
    "Cuánto se gasta en viáticos, cómo evoluciona y qué clientes, candidatos y montos lo explican.",
    usa_periodo=False, icono="bi-speedometer2", filtros=s.FILTROS_RESUMEN,
)
def resumen(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_viaticos, SUM({IMPORTE}) AS monto_total, AVG({IMPORTE}) AS promedio_viatico,
               COUNT(DISTINCT a.AsignacionId) AS asignaciones_con_viaticos, COUNT(DISTINCT p.PedidoId) AS pedidos_con_viaticos
        {DESDE} WHERE {w}""", p)
    este_mes = num(sgo.valor(f"SELECT COUNT(*) AS viaticos_este_mes {DESDE} WHERE YEAR({FECHA}) = YEAR(GETDATE()) "
                             f"AND MONTH({FECHA}) = MONTH(GETDATE())"))
    evolucion = sgo.filas(f"""
        SELECT YEAR({FECHA}) AS anio, MONTH({FECHA}) AS mes, COUNT(*) AS cantidad, SUM({IMPORTE}) AS monto_total
        {DESDE} WHERE {w} AND {FECHA_VALIDA} AND YEAR({FECHA}) >= YEAR(GETDATE()) - 2
        GROUP BY YEAR({FECHA}), MONTH({FECHA}) ORDER BY anio, mes""", p)
    clientes = sgo.filas(f"""
        SELECT TOP 15 RTRIM(c.ClienteNombre) AS label, COUNT(*) AS cantidad_viaticos, SUM({IMPORTE}) AS monto_total,
               AVG({IMPORTE}) AS promedio
        {DESDE} {JOIN_CLI} WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre ORDER BY monto_total DESC""", p)
    case_r = "CASE " + " ".join(f"WHEN {c} THEN '{e}'" for e, c in _RANGOS_IMPORTE[:-1]) + f" ELSE '{_RANGOS_IMPORTE[-1][0]}' END"
    importes = sgo.filas(f"""
        SELECT {case_r} AS label, COUNT(*) AS cantidad, SUM({IMPORTE}) AS monto_total, MIN({IMPORTE}) AS orden
        {DESDE} WHERE {w} GROUP BY {case_r} ORDER BY orden""", p)
    candidatos = sgo.filas(f"""
        SELECT TOP 15 {CANDIDATO} AS label, COUNT(*) AS cantidad_viaticos, SUM({IMPORTE}) AS monto_total, AVG({IMPORTE}) AS promedio
        {DESDE} {JOIN_CAND} WHERE {w}
        GROUP BY cand.CandidatoId, cand.CandidatoNombre, cand.CandidatoApellido ORDER BY monto_total DESC""", p)
    promedio_cliente = sgo.filas(f"""
        SELECT TOP 15 RTRIM(c.ClienteNombre) AS label, AVG({IMPORTE}) AS promedio
        {DESDE} {JOIN_CLI} WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre HAVING COUNT(*) >= 3 ORDER BY promedio DESC""", p)
    mes_actual = sgo.filas(f"""
        SELECT DAY({FECHA}) AS dia, COUNT(*) AS cantidad, SUM({IMPORTE}) AS monto
        {DESDE} WHERE {w} AND YEAR({FECHA}) = YEAR(GETDATE()) AND MONTH({FECHA}) = MONTH(GETDATE())
        GROUP BY DAY({FECHA}) ORDER BY dia""", p)

    pico = max(evolucion, key=lambda r: num(r["monto_total"]), default=None)
    secciones = [
        seccion(
            "Evolución mensual (últimos 2 años)",
            [f"El mes de mayor gasto fue {_ym(pico)} con {monto(pico['monto_total'])}." if pico else ""],
            g.lineas([_ym(r) for r in evolucion], {"Monto": valores(evolucion, "monto_total")}, formato="fmt:pesos_k", area=True),
            explicacion="Suma de importes de viáticos por mes (HistorialViaticosFecha) desde hace dos años.",
            detalle="mes", ayuda_detalle="Hacé clic en un mes para ver sus viáticos.",
            tabla=tabla("Por mes", ["Mes", "Viáticos", "Monto"],
                        [[_ym(r), entero(r["cantidad"]), monto(r["monto_total"])] for r in evolucion[-12:]]),
        ),
        seccion(
            "Top clientes por monto total",
            [lider(clientes, "label", "monto_total", "", "el top 15").replace(" encabeza con ", " encabeza: "),
             concentracion(clientes, "monto_total", 3, "gasto del top 15")],
            g.ranking(etiquetas(clientes), valores(clientes, "monto_total"), "Monto", formato="fmt:pesos_k"),
            alto=g.alto_ranking(len(clientes)),
            explicacion="Clientes con mayor gasto en viáticos de sus asignaciones.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus viáticos.",
        ),
        seccion(
            "Distribución por rango de importes",
            [lider(importes, "label", "cantidad", "viáticos")],
            g.columnas(etiquetas(importes), {"Viáticos": valores(importes, "cantidad")}, rotar=0),
            explicacion="Cantidad de viáticos según su importe.",
            detalle="rango", ayuda_detalle="Hacé clic en un rango para ver esos viáticos.",
        ),
        seccion(
            "Top candidatos por monto total",
            [concentracion(candidatos, "monto_total", 3, "gasto del top 15")],
            g.ranking(etiquetas(candidatos), valores(candidatos, "monto_total"), "Monto", g.SERIES[1], formato="fmt:pesos_k"),
            alto=g.alto_ranking(len(candidatos)),
            explicacion="Personas asignadas con mayor monto de viáticos.",
            detalle="candidato", ayuda_detalle="Hacé clic en un candidato para ver sus viáticos.",
        ),
        seccion(
            "Promedio por cliente (mínimo 3 viáticos)",
            [extremos(promedio_cliente, "label", "promedio", monto, "promedio más alto", "más bajo")],
            g.ranking(etiquetas(promedio_cliente), valores(promedio_cliente, "promedio"), "Promedio", g.SERIES[2],
                      formato="fmt:pesos"),
            alto=g.alto_ranking(len(promedio_cliente)),
            explicacion="Importe promedio por viático de cada cliente con 3 viáticos o más.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus viáticos.",
        ),
        seccion(
            "Viáticos del mes actual por día",
            [f"Este mes van {entero(total(mes_actual, 'cantidad'))} viáticos por {monto(total(mes_actual, 'monto'))}."],
            g.columnas([str(int(num(r["dia"]))) for r in mes_actual], {"Monto": valores(mes_actual, "monto")},
                       formato="fmt:pesos_k", rotar=0),
            explicacion="Monto de viáticos de cada día del mes en curso.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total viáticos", entero(k.get("total_viaticos"))),
            kpi("Monto total", monto_corto(k.get("monto_total"))),
            kpi("Promedio por viático", monto(k.get("promedio_viatico"))),
            kpi("Asignaciones con viáticos", entero(k.get("asignaciones_con_viaticos"))),
            kpi("Pedidos con viáticos", entero(k.get("pedidos_con_viaticos"))),
            kpi("Viáticos este mes", entero(este_mes)),
        ],
        "conclusiones": [
            f"Se registraron {entero(k.get('total_viaticos'))} viáticos por {monto(k.get('monto_total'))} "
            f"(promedio {monto(k.get('promedio_viatico'))}).",
            lider(clientes, "label", "monto_total", "", "el gasto del top 15").replace(" encabeza con ", " encabeza "),
            lider(importes, "label", "cantidad", "viáticos"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué clientes gastan más en viáticos?", "¿Cómo viene el gasto mensual?"],
        "contexto_ia": {"kpis": k, "evolucion": evolucion, "clientes": clientes, "importes": importes},
    }


@catalogo.detalle("resumen")
def detalle_resumen(clave, valor, serie, periodo, filtros):
    condicion, params, orden = "", [], f"{FECHA} DESC"
    if clave == "cliente":
        condicion, params = "RTRIM(cl.ClienteNombre) = %s", [valor]
    elif clave == "candidato":
        condicion, params = "RTRIM(cand.CandidatoNombre) + ' ' + RTRIM(cand.CandidatoApellido) = %s", [valor]
    elif clave == "rango":
        condicion, orden = next((c for e, c in _RANGOS_IMPORTE if e == valor), "1=0"), f"{IMPORTE} DESC"
    elif clave == "mes":
        condicion, params = f"FORMAT({FECHA}, 'yyyy-MM') = %s", [valor]
    return respuesta_detalle(f"Viáticos · {valor}", s.COLUMNAS_VIATICO, s.viaticos(filtros, condicion, params, orden))


# ==========================================================================
# 2. Análisis temporal (via_tem)
# ==========================================================================
@catalogo.registrar(
    "temporal", "Análisis temporal",
    "Qué días, meses y trimestres concentran los viáticos, comparación entre años y crecimiento mes a mes.",
    usa_periodo=False, icono="bi-calendar3", filtros=s.FILTROS_ANIO,
)
def temporal(periodo, filtros):
    w, p = where(filtros)
    wc, pc = where(filtros, con_anio=False)  # la comparativa entre años no usa el filtro de año
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_viaticos, SUM({IMPORTE}) AS monto_total, AVG({IMPORTE}) AS promedio,
               MAX({IMPORTE}) AS maximo, MIN({IMPORTE}) AS minimo
        {DESDE} WHERE {w}""", p)
    meses_cmp = sgo.fila(f"""
        SELECT COUNT(CASE WHEN YEAR({FECHA}) = YEAR(GETDATE()) AND MONTH({FECHA}) = MONTH(GETDATE()) THEN 1 END) AS mes_actual,
               COUNT(CASE WHEN YEAR({FECHA}) = YEAR(DATEADD(MONTH, -1, GETDATE()))
                           AND MONTH({FECHA}) = MONTH(DATEADD(MONTH, -1, GETDATE())) THEN 1 END) AS mes_anterior
        {DESDE}""")
    semana = sgo.filas(f"""
        SELECT DATEPART(WEEKDAY, {FECHA}) AS dia_semana, COUNT(*) AS cantidad, SUM({IMPORTE}) AS monto_total, AVG({IMPORTE}) AS promedio
        {DESDE} WHERE {w} AND {FECHA} IS NOT NULL GROUP BY DATEPART(WEEKDAY, {FECHA}) ORDER BY dia_semana""", p)
    estacional = sgo.filas(f"""
        SELECT MONTH({FECHA}) AS mes, COUNT(*) AS cantidad, SUM({IMPORTE}) AS monto_total, AVG({IMPORTE}) AS promedio
        {DESDE} WHERE {w} AND {FECHA} IS NOT NULL GROUP BY MONTH({FECHA}) ORDER BY mes""", p)
    comparativa = sgo.filas(f"""
        SELECT YEAR({FECHA}) AS anio, MONTH({FECHA}) AS mes, COUNT(*) AS cantidad, SUM({IMPORTE}) AS monto_total
        {DESDE} WHERE {wc} AND {FECHA_VALIDA} AND YEAR({FECHA}) >= YEAR(GETDATE()) - 2
        GROUP BY YEAR({FECHA}), MONTH({FECHA}) ORDER BY anio, mes""", pc)
    trimestres = sgo.filas(f"""
        SELECT YEAR({FECHA}) AS anio, DATEPART(QUARTER, {FECHA}) AS trimestre, COUNT(*) AS cantidad, SUM({IMPORTE}) AS monto_total
        {DESDE} WHERE {w} AND {FECHA_VALIDA} GROUP BY YEAR({FECHA}), DATEPART(QUARTER, {FECHA}) ORDER BY anio, trimestre""", p)
    acumulado = sgo.filas(f"""
        SELECT anio, mes, monto_mes, SUM(monto_mes) OVER (ORDER BY anio, mes ROWS UNBOUNDED PRECEDING) AS acumulado
        FROM (SELECT YEAR({FECHA}) AS anio, MONTH({FECHA}) AS mes, SUM({IMPORTE}) AS monto_mes
              {DESDE} WHERE {w} AND {FECHA_VALIDA} AND YEAR({FECHA}) = YEAR(GETDATE())
              GROUP BY YEAR({FECHA}), MONTH({FECHA})) x ORDER BY anio, mes""", p)
    crecimiento = sgo.filas(f"""
        SELECT anio, mes, monto_total, monto_mes_anterior,
               CASE WHEN monto_mes_anterior > 0 THEN ((monto_total - monto_mes_anterior) * 100.0 / monto_mes_anterior) ELSE 0 END AS crecimiento_porcentual
        FROM (SELECT YEAR({FECHA}) AS anio, MONTH({FECHA}) AS mes, SUM({IMPORTE}) AS monto_total,
                     LAG(SUM({IMPORTE}), 1, 0) OVER (ORDER BY YEAR({FECHA}), MONTH({FECHA})) AS monto_mes_anterior
              {DESDE} WHERE {w} AND {FECHA_VALIDA} AND YEAR({FECHA}) >= YEAR(GETDATE()) - 1
              GROUP BY YEAR({FECHA}), MONTH({FECHA})) x ORDER BY anio, mes""", p)

    def dia(r):
        try:
            return DIAS[int(num(r["dia_semana"]))]
        except (KeyError, ValueError, TypeError):
            return str(r["dia_semana"])

    def nombre_mes(r):
        try:
            return MESES[int(num(r["mes"])) - 1]
        except (IndexError, ValueError, TypeError):
            return str(r["mes"])

    por_anio = defaultdict(lambda: [None] * 12)
    for r in comparativa:
        try:
            por_anio[str(int(num(r["anio"])))][int(num(r["mes"])) - 1] = num(r["monto_total"])
        except (ValueError, IndexError, TypeError):
            pass
    trim_anio = defaultdict(lambda: [None] * 4)
    for r in trimestres:
        try:
            trim_anio[str(int(num(r["anio"])))][int(num(r["trimestre"])) - 1] = num(r["monto_total"])
        except (ValueError, IndexError, TypeError):
            pass
    crec = [r for r in crecimiento if num(r.get("monto_mes_anterior"))]
    grafico_crec = g.columnas([_ym(r) for r in crec], {"Crecimiento": [round(num(r["crecimiento_porcentual"]), 1) for r in crec]},
                              formato="fmt:pct")
    grafico_crec["series"][0]["data"] = [{"value": round(num(r["crecimiento_porcentual"]), 1),
                                          "itemStyle": {"color": g.POSITIVO if num(r["crecimiento_porcentual"]) >= 0 else g.NEGATIVO}}
                                         for r in crec]
    var_mes = proporcion(num(meses_cmp.get("mes_actual")) - num(meses_cmp.get("mes_anterior")), meses_cmp.get("mes_anterior"))
    pico_dia = max(semana, key=lambda r: num(r["cantidad"]), default=None)
    pico_mes = max(estacional, key=lambda r: num(r["monto_total"]), default=None)
    secciones = [
        seccion(
            "Viáticos por día de la semana",
            [f"El día con más viáticos es el {dia(pico_dia).lower()} ({entero(pico_dia['cantidad'])})." if pico_dia else ""],
            g.columnas([dia(r) for r in semana], {"Viáticos": valores(semana, "cantidad")}, rotar=0),
            explicacion="Cantidad de viáticos según el día de la semana de su fecha.",
            detalle="dia", ayuda_detalle="Hacé clic en un día para ver esos viáticos.",
        ),
        seccion(
            "Estacionalidad por mes del año",
            [f"{nombre_mes(pico_mes)} es el mes de mayor gasto ({monto(pico_mes['monto_total'])})." if pico_mes else ""],
            g.columnas([nombre_mes(r) for r in estacional], {"Monto": valores(estacional, "monto_total")}, formato="fmt:pesos_k"),
            explicacion="Monto total por mes del año, sumando todos los años del filtro.",
            detalle="mes_anio", ayuda_detalle="Hacé clic en un mes para ver esos viáticos.",
        ),
        seccion(
            "Comparativa de los últimos 3 años por mes",
            [],
            g.lineas([m[:3] for m in MESES], {a: por_anio[a] for a in sorted(por_anio)[-3:]}, formato="fmt:pesos_k"),
            explicacion="Monto mensual de cada año, superpuestos para comparar el mismo mes. No usa el filtro de año.",
        ),
        seccion(
            "Viáticos por trimestre",
            [],
            g.columnas(["T1", "T2", "T3", "T4"], {a: trim_anio[a] for a in sorted(trim_anio)[-4:]}, formato="fmt:pesos_k", rotar=0),
            explicacion="Monto por trimestre; cada color es un año.",
        ),
        seccion(
            "Acumulado mensual del año actual",
            [f"En lo que va del año se acumulan {monto(acumulado[-1]['acumulado'])}." if acumulado else ""],
            g.lineas([nombre_mes(r)[:3] for r in acumulado], {"Acumulado": valores(acumulado, "acumulado")},
                     formato="fmt:pesos_k", area=True),
            explicacion="Suma corrida del monto de viáticos mes a mes en el año en curso.",
        ),
        seccion(
            "Crecimiento % mes a mes (último año)",
            [f"El gasto subió respecto del mes anterior en {sum(1 for r in crec if num(r['crecimiento_porcentual']) > 0)} "
             f"de {len(crec)} meses." if crec else ""],
            grafico_crec,
            explicacion="Variación del monto de cada mes contra el anterior: azul si subió, rojo si bajó.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total viáticos", entero(k.get("total_viaticos"))),
            kpi("Monto total", monto_corto(k.get("monto_total"))),
            kpi("Promedio", monto(k.get("promedio"))),
            kpi("Máximo", monto(k.get("maximo"))),
            kpi("Mínimo", monto(k.get("minimo"))),
            kpi("Crecimiento mensual", pct(var_mes) if num(meses_cmp.get("mes_anterior")) else "—",
                f"{entero(meses_cmp.get('mes_actual'))} este mes vs. {entero(meses_cmp.get('mes_anterior'))} el anterior",
                "Cantidad de viáticos de este mes contra el mes anterior."),
        ],
        "conclusiones": [
            f"El día con más viáticos es el {dia(pico_dia).lower()}." if pico_dia else "",
            f"{nombre_mes(pico_mes)} es el mes de mayor gasto." if pico_mes else "",
            f"En lo que va del año se gastaron {monto(acumulado[-1]['acumulado'])}." if acumulado else "",
        ],
        "secciones": secciones,
        "sugerencias": ["¿En qué meses se gasta más en viáticos?", "¿El gasto crece respecto del año pasado?"],
        "contexto_ia": {"kpis": k, "semana": semana, "estacional": estacional, "trimestres": trimestres},
    }


@catalogo.detalle("temporal")
def detalle_temporal(clave, valor, serie, periodo, filtros):
    if clave == "dia":
        numero = next((n for n, d in DIAS.items() if d == valor), 0)
        condicion, params = f"DATEPART(WEEKDAY, {FECHA}) = %s", [numero]
    else:
        numero = MESES.index(valor) + 1 if valor in MESES else 0
        condicion, params = f"MONTH({FECHA}) = %s", [numero]
    return respuesta_detalle(f"Viáticos · {valor}", s.COLUMNAS_VIATICO, s.viaticos(filtros, condicion, params))


# ==========================================================================
# 3. Observaciones (via_txt)
# ==========================================================================
@catalogo.registrar(
    "observaciones", "Análisis de observaciones",
    "En qué se gastan los viáticos según sus observaciones y qué tan bien se documentan.",
    usa_periodo=False, icono="bi-card-text", filtros=s.FILTROS_ANIO,
)
def observaciones(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_viaticos, SUM(CASE WHEN {OBS} != '' THEN 1 ELSE 0 END) AS con_observaciones,
               SUM(CASE WHEN {OBS} = '' THEN 1 ELSE 0 END) AS sin_observaciones, AVG(LEN({OBS})) AS longitud_promedio
        {DESDE} WHERE {w}""", p)
    partes = [f"SELECT '{nombre}' AS categoria, {IMPORTE} AS importe {DESDE} WHERE {w} AND {s.condicion_categoria(nombre)}"
              for nombre in list(s.CATEGORIAS) + ["Otros"]]
    categorias = sgo.filas(f"""
        SELECT categoria AS label, COUNT(*) AS cantidad, SUM(importe) AS monto_total, AVG(importe) AS promedio
        FROM ({' UNION ALL '.join(partes)}) x GROUP BY categoria ORDER BY monto_total DESC""", p * len(partes))
    largo = f"LEN({OBS})"
    rangos = ["Sin texto (0)", "Muy corto (1-20)", "Corto (21-50)", "Medio (51-100)", "Largo (101-200)", "Muy largo (200+)"]
    case_l = (f"CASE WHEN {largo} = 0 THEN '{rangos[0]}' WHEN {largo} <= 20 THEN '{rangos[1]}' WHEN {largo} <= 50 THEN '{rangos[2]}' "
              f"WHEN {largo} <= 100 THEN '{rangos[3]}' WHEN {largo} <= 200 THEN '{rangos[4]}' ELSE '{rangos[5]}' END")
    longitud = sgo.filas(f"""SELECT {case_l} AS label, COUNT(*) AS cantidad, SUM({IMPORTE}) AS monto_total
                             {DESDE} WHERE {w} GROUP BY {case_l} ORDER BY MIN({largo})""", p)
    partes_p = [f"SELECT '{pal}' AS palabra, COUNT(*) AS frecuencia, SUM({IMPORTE}) AS monto_total {DESDE} "
                f"WHERE {w} AND {s.contiene(pal)}" for pal in s.PALABRAS_FRECUENTES]
    palabras = sgo.filas(f"SELECT TOP 15 palabra AS label, frecuencia, monto_total FROM ({' UNION ALL '.join(partes_p)}) x "
                         "WHERE frecuencia > 0 ORDER BY frecuencia DESC", p * len(partes_p))
    calidad = sgo.filas(f"""
        SELECT TOP 15 RTRIM(c.ClienteNombre) AS label, COUNT(*) AS total_viaticos,
               SUM(CASE WHEN {OBS} != '' THEN 1 ELSE 0 END) AS con_obs,
               CAST(SUM(CASE WHEN {OBS} != '' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS DECIMAL(5,2)) AS porcentaje_documentado,
               AVG(LEN({OBS})) AS longitud_promedio
        {DESDE} {JOIN_CLI} WHERE {w} GROUP BY c.ClienteId, c.ClienteNombre HAVING COUNT(*) >= 5
        ORDER BY porcentaje_documentado DESC""", p)

    pct_doc = proporcion(k.get("con_observaciones"), k.get("total_viaticos"))
    secciones = [
        seccion(
            "Categorías de gasto detectadas",
            [lider(categorias, "label", "monto_total", "", "lo categorizado").replace(" encabeza con ", " encabeza: "),
             "Un viático puede caer en más de una categoría si su observación menciona varias cosas."],
            g.ranking(etiquetas(categorias), valores(categorias, "monto_total"), "Monto", formato="fmt:pesos_k"),
            alto=g.alto_ranking(len(categorias)),
            explicacion="Categoría según palabras en la observación (combustible, peaje, comida, hotel, taxi, …). "
                        "«Otros»: tiene observación pero no menciona ninguna palabra conocida.",
            detalle="categoria", ayuda_detalle="Hacé clic en una categoría para ver esos viáticos.",
            tabla=tabla("Por categoría", ["Categoría", "Viáticos", "Monto", "Promedio"],
                        [[r["label"], entero(r["cantidad"]), monto(r["monto_total"]), monto(r["promedio"])] for r in categorias]),
        ),
        seccion(
            "Estado de la documentación",
            [f"{pct(pct_doc)} de los viáticos tiene observación."],
            g.torta([("Con observaciones", num(k.get("con_observaciones"))), ("Sin observaciones", num(k.get("sin_observaciones")))],
                    colores=[g.SERIES[0], g.NEGATIVO]),
            explicacion="Viáticos con y sin texto en la observación.",
            detalle="documentacion", ayuda_detalle="Hacé clic en una porción para ver esos viáticos.",
        ),
        seccion(
            "Top 15 palabras más frecuentes",
            [lider(palabras, "label", "frecuencia", "menciones")],
            g.ranking(etiquetas(palabras), valores(palabras, "frecuencia"), "Viáticos", g.SERIES[1]),
            alto=g.alto_ranking(len(palabras)),
            explicacion="Cuántos viáticos mencionan cada palabra de una lista de términos habituales.",
            detalle="palabra", ayuda_detalle="Hacé clic en una palabra para ver esos viáticos.",
        ),
        seccion(
            "Distribución por longitud de las observaciones",
            [lider(longitud, "label", "cantidad", "viáticos")],
            g.columnas(etiquetas(longitud), {"Viáticos": valores(longitud, "cantidad")}),
            explicacion="Viáticos según la cantidad de caracteres de su observación.",
        ),
        seccion(
            "Calidad de documentación por cliente",
            [extremos(calidad, "label", "porcentaje_documentado", pct, "mejor documentado", "peor")],
            g.ranking(etiquetas(calidad), valores(calidad, "porcentaje_documentado"), "% documentado", g.SERIES[2],
                      formato="fmt:pct"),
            alto=g.alto_ranking(len(calidad)),
            explicacion="Parte de los viáticos de cada cliente (5 o más) que tiene observación.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total viáticos", entero(k.get("total_viaticos"))),
            kpi("Con observaciones", entero(k.get("con_observaciones"))),
            kpi("Sin observaciones", entero(k.get("sin_observaciones")), "", alerta=num(k.get("sin_observaciones")) > 0),
            kpi("% documentado", pct(pct_doc)),
            kpi("Longitud promedio", f"{entero(k.get('longitud_promedio'))} caracteres"),
            kpi("Categorías detectadas", entero(len(categorias))),
        ],
        "conclusiones": [
            f"{pct(pct_doc)} de los viáticos está documentado con una observación.",
            lider(categorias, "label", "monto_total", "", "lo categorizado").replace(" encabeza con ", " es la categoría de mayor gasto: "),
            extremos(calidad, "label", "porcentaje_documentado", pct, "cliente mejor documentado", "peor"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿En qué se gasta más?", "¿Qué clientes documentan peor los viáticos?"],
        "contexto_ia": {"kpis": k, "categorias": categorias, "palabras": palabras},
    }


@catalogo.detalle("observaciones")
def detalle_observaciones(clave, valor, serie, periodo, filtros):
    if clave == "categoria":
        condicion = s.condicion_categoria(valor)
    elif clave == "palabra":
        condicion = s.contiene(valor) if valor in s.PALABRAS_FRECUENTES else "1=0"
    else:
        condicion = f"{OBS} != ''" if valor == "Con observaciones" else f"{OBS} = ''"
    return respuesta_detalle(f"Viáticos · {valor}", s.COLUMNAS_VIATICO, s.viaticos(filtros, condicion))


# ==========================================================================
# 4. Detección de anomalías (via_ano)
# ==========================================================================
_PERIODOS_MES = [("Inicio de mes (1-5)", f"DAY({FECHA}) <= 5"), ("Días 6-10", f"DAY({FECHA}) BETWEEN 6 AND 10"),
                 ("Días 11-15", f"DAY({FECHA}) BETWEEN 11 AND 15"), ("Días 16-20", f"DAY({FECHA}) BETWEEN 16 AND 20"),
                 ("Días 21-25", f"DAY({FECHA}) BETWEEN 21 AND 25"), ("Fin de mes (26-31)", f"DAY({FECHA}) >= 26")]


def _estadisticas(filtros):
    w, p = where(filtros)
    st = sgo.fila(f"SELECT AVG({IMPORTE}) AS promedio, STDEV({IMPORTE}) AS desv_std {DESDE} WHERE {w}", p)
    return num(st.get("promedio")), num(st.get("desv_std"))


@catalogo.registrar(
    "anomalias", "Detección de anomalías",
    "Importes fuera de lo normal, duplicados, varios viáticos el mismo día, concentración a fin de mes y meses atípicos.",
    usa_periodo=False, icono="bi-exclamation-triangle", filtros=s.FILTROS_ANIO,
)
def anomalias(periodo, filtros):
    w, p = where(filtros)
    total_v = num(sgo.valor(f"SELECT COUNT(*) AS total {DESDE} WHERE {w}", p))
    promedio, desvio = _estadisticas(filtros)
    limite_sup, limite_inf = promedio + 3 * desvio, max(0, promedio - 3 * desvio)
    outliers = sgo.fila(f"""
        SELECT COUNT(CASE WHEN {IMPORTE} > %s THEN 1 END) AS altos, COUNT(CASE WHEN {IMPORTE} < %s THEN 1 END) AS bajos
        {DESDE} WHERE {w}""", [limite_sup, limite_inf] + p) if desvio else {"altos": 0, "bajos": 0}
    duplicados = sgo.filas(f"""
        SELECT CONVERT(VARCHAR(10), {FECHA}, 103) AS fecha, {IMPORTE} AS importe, {CANDIDATO} AS candidato,
               RTRIM(c.ClienteNombre) AS cliente, COUNT(*) AS cantidad_duplicados
        {DESDE} {JOIN_CLI} {JOIN_CAND} WHERE {w}
        GROUP BY CONVERT(VARCHAR(10), {FECHA}, 103), {IMPORTE}, cand.CandidatoId, cand.CandidatoNombre, cand.CandidatoApellido,
                 c.ClienteNombre
        HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC, {IMPORTE} DESC""", p)
    multiples = sgo.filas(f"""
        SELECT TOP 30 CONVERT(VARCHAR(10), {FECHA}, 103) AS fecha, {CANDIDATO} AS candidato, RTRIM(c.ClienteNombre) AS cliente,
               COUNT(*) AS cantidad_viaticos, SUM({IMPORTE}) AS monto_total
        {DESDE} {JOIN_CLI} {JOIN_CAND} WHERE {w}
        GROUP BY CONVERT(VARCHAR(10), {FECHA}, 103), cand.CandidatoId, cand.CandidatoNombre, cand.CandidatoApellido, c.ClienteNombre
        HAVING COUNT(*) >= 3 ORDER BY COUNT(*) DESC, SUM({IMPORTE}) DESC""", p)
    case_d = "CASE " + " ".join(f"WHEN {c} THEN '{e}'" for e, c in _PERIODOS_MES[:-1]) + f" ELSE '{_PERIODOS_MES[-1][0]}' END"
    fin_mes = sgo.filas(f"""
        SELECT {case_d} AS label, COUNT(*) AS cantidad, SUM({IMPORTE}) AS monto_total, AVG({IMPORTE}) AS promedio
        {DESDE} WHERE {w} AND {FECHA} IS NOT NULL GROUP BY {case_d} ORDER BY MIN(DAY({FECHA}))""", p)
    por_cliente = sgo.filas(f"""
        SELECT TOP 15 cliente AS label, total_viaticos, outliers_altos, outliers_bajos,
               (outliers_altos + outliers_bajos) AS total_outliers,
               CAST((outliers_altos + outliers_bajos) * 100.0 / total_viaticos AS DECIMAL(5,2)) AS porcentaje_outliers
        FROM (SELECT RTRIM(c.ClienteNombre) AS cliente, COUNT(*) AS total_viaticos,
                     SUM(CASE WHEN (importe - promedio) / NULLIF(desv_std, 0) > 3 THEN 1 ELSE 0 END) AS outliers_altos,
                     SUM(CASE WHEN (promedio - importe) / NULLIF(desv_std, 0) > 3 THEN 1 ELSE 0 END) AS outliers_bajos
              FROM (SELECT {IMPORTE} AS importe, p.ClienteId,
                           AVG({IMPORTE}) OVER (PARTITION BY p.ClienteId) AS promedio,
                           STDEV({IMPORTE}) OVER (PARTITION BY p.ClienteId) AS desv_std
                    {DESDE} WHERE {w}) cs
              INNER JOIN dbo.Clientes c ON cs.ClienteId = c.ClienteId
              GROUP BY c.ClienteId, c.ClienteNombre HAVING COUNT(*) >= 10) x
        WHERE (outliers_altos + outliers_bajos) > 0 ORDER BY porcentaje_outliers DESC""", p)
    picos = sgo.filas(f"""
        SELECT anio, mes, monto_mes, promedio_historico,
               CAST((monto_mes - promedio_historico) * 100.0 / NULLIF(promedio_historico, 0) AS DECIMAL(10,2)) AS variacion_porcentual,
               CASE WHEN monto_mes > promedio_historico * 1.5 THEN 'Pico alto' WHEN monto_mes < promedio_historico * 0.5 THEN 'Caída brusca'
                    ELSE 'Normal' END AS tipo_anomalia
        FROM (SELECT anio, mes, monto_mes, AVG(monto_mes) OVER () AS promedio_historico
              FROM (SELECT YEAR({FECHA}) AS anio, MONTH({FECHA}) AS mes, SUM({IMPORTE}) AS monto_mes
                    {DESDE} WHERE {w} AND {FECHA} IS NOT NULL AND YEAR({FECHA}) >= YEAR(GETDATE()) - 2
                    GROUP BY YEAR({FECHA}), MONTH({FECHA})) m) x
        WHERE monto_mes > promedio_historico * 1.5 OR monto_mes < promedio_historico * 0.5
        ORDER BY ABS(monto_mes - promedio_historico) DESC""", p)
    obs = sgo.fila(f"""SELECT SUM(CASE WHEN {OBS} != '' THEN 1 ELSE 0 END) AS con_observaciones,
                              SUM(CASE WHEN {OBS} = '' THEN 1 ELSE 0 END) AS sin_observaciones {DESDE} WHERE {w}""", p)

    n_out = num(outliers.get("altos")) + num(outliers.get("bajos"))
    total_anomalias = n_out + len(duplicados) + len(multiples)
    fin = next((r for r in fin_mes if str(r["label"]).startswith("Fin")), None)
    secciones = [
        seccion(
            "Viáticos con importes extremos",
            [f"{entero(outliers.get('altos'))} viáticos superan {monto(limite_sup)} (promedio + 3 desvíos) y "
             f"{entero(outliers.get('bajos'))} quedan por debajo de {monto(limite_inf)}."],
            g.columnas(["Muy altos", "Muy bajos"], {"Viáticos": [num(outliers.get("altos")), num(outliers.get("bajos"))]},
                       rotar=0, colores=[g.NEGATIVO]),
            explicacion="Viáticos a más de 3 desvíos estándar del importe promedio (z-score mayor a 3).",
            detalle="outlier", ayuda_detalle="Hacé clic en una barra para ver esos viáticos.",
        ),
        seccion(
            "Viáticos sin observaciones",
            [f"{entero(obs.get('sin_observaciones'))} viáticos no tienen observación."],
            g.torta([("Con observaciones", num(obs.get("con_observaciones"))), ("Sin observaciones", num(obs.get("sin_observaciones")))],
                    colores=[g.SERIES[0], g.NEGATIVO]),
            explicacion="Un viático sin observación no permite saber en qué se gastó.",
            detalle="observacion", ayuda_detalle="Hacé clic en una porción para ver esos viáticos.",
        ),
        seccion(
            "Distribución por período del mes",
            [f"{pct(proporcion(fin['cantidad'], total(fin_mes, 'cantidad')))} de los viáticos se carga a fin de mes."
             if fin else ""],
            g.columnas(etiquetas(fin_mes), {"Viáticos": valores(fin_mes, "cantidad")}),
            explicacion="Viáticos según el día del mes. Una concentración fuerte a fin de mes puede indicar cargas acumuladas.",
            detalle="periodo_mes", ayuda_detalle="Hacé clic en un período para ver esos viáticos.",
        ),
        seccion(
            "Clientes con más viáticos atípicos (%)",
            [extremos(por_cliente, "label", "porcentaje_outliers", pct, "mayor proporción", "menor")],
            g.ranking(etiquetas(por_cliente), valores(por_cliente, "porcentaje_outliers"), "% atípicos", g.NEGATIVO,
                      formato="fmt:pct"),
            alto=g.alto_ranking(len(por_cliente)),
            explicacion="Para cada cliente (10+ viáticos), qué parte de sus viáticos se aleja más de 3 desvíos de su "
                        "propio promedio.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus viáticos.",
        ),
        seccion(
            "Duplicados: mismo candidato, fecha e importe",
            [f"{entero(len(duplicados))} combinaciones repetidas." if duplicados else "No se encontraron duplicados."],
            tabla=tabla("Duplicados sospechosos", ["Fecha", "Candidato", "Cliente", "Importe", "Repeticiones"],
                        [[r["fecha"], r["candidato"], r["cliente"], monto(r["importe"]), entero(r["cantidad_duplicados"])]
                         for r in duplicados[:50]]),
            explicacion="Viáticos del mismo candidato, mismo día y mismo importe registrados más de una vez.",
        ),
        seccion(
            "Varios viáticos el mismo día (3 o más)",
            [],
            tabla=tabla("Mismo candidato, mismo día", ["Fecha", "Candidato", "Cliente", "Cantidad", "Monto total"],
                        [[r["fecha"], r["candidato"], r["cliente"], entero(r["cantidad_viaticos"]), monto(r["monto_total"])]
                         for r in multiples]),
            explicacion="Candidatos con 3 viáticos o más en un mismo día.",
        ),
        seccion(
            "Meses atípicos",
            [],
            tabla=tabla("Picos y caídas", ["Mes", "Monto", "Promedio histórico", "Variación", "Tipo"],
                        [[_ym(r), monto(r["monto_mes"]), monto(r["promedio_historico"]), pct(r["variacion_porcentual"]),
                          r["tipo_anomalia"]] for r in picos]),
            explicacion="Meses de los últimos dos años con un gasto 50% por encima o por debajo del promedio mensual.",
        ),
    ]
    return {
        "kpis": [
            kpi("Anomalías detectadas", entero(total_anomalias), "extremos + duplicados + múltiples",
                alerta=total_anomalias > 0),
            kpi("Importes extremos", entero(n_out), "muy altos o muy bajos"),
            kpi("Duplicados sospechosos", entero(len(duplicados)), "", alerta=len(duplicados) > 0),
            kpi("Promedio normal", monto(promedio), f"desvío {monto(desvio)}"),
            kpi("Límite de alerta", monto(limite_sup), "promedio + 3 desvíos"),
        ],
        "conclusiones": [
            f"Se detectaron {entero(total_anomalias)} anomalías en {entero(total_v)} viáticos.",
            f"{entero(n_out)} importes extremos y {entero(len(duplicados))} posibles duplicados.",
            f"{entero(obs.get('sin_observaciones'))} viáticos no tienen observación.",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué clientes tienen más viáticos atípicos?", "¿Hay duplicados para revisar?"],
        "contexto_ia": {"promedio": promedio, "desvio": desvio, "outliers": outliers, "fin_mes": fin_mes,
                        "por_cliente": por_cliente, "duplicados": len(duplicados), "multiples": len(multiples)},
    }


@catalogo.detalle("anomalias")
def detalle_anomalias(clave, valor, serie, periodo, filtros):
    params, orden = [], f"{FECHA} DESC"
    if clave == "outlier":
        promedio, desvio = _estadisticas(filtros)
        if valor == "Muy altos":
            condicion, params = f"{IMPORTE} > %s", [promedio + 3 * desvio]
        else:
            condicion, params = f"{IMPORTE} < %s", [max(0, promedio - 3 * desvio)]
        orden = f"ABS({IMPORTE} - {promedio}) DESC"
    elif clave == "observacion":
        condicion = f"{OBS} != ''" if valor == "Con observaciones" else f"{OBS} = ''"
    elif clave == "periodo_mes":
        condicion = next((c for e, c in _PERIODOS_MES if e == valor), "1=0")
    else:
        condicion, params = "RTRIM(cl.ClienteNombre) = %s", [valor]
    return respuesta_detalle(f"Viáticos · {valor}", s.COLUMNAS_VIATICO, s.viaticos(filtros, condicion, params, orden))


# ==========================================================================
# 5. Análisis por cliente (via_cli)
# ==========================================================================
@catalogo.registrar(
    "clientes", "Análisis por cliente",
    "Ranking, concentración, viáticos por asignación, evolución y comparación anual del gasto de cada cliente.",
    usa_periodo=False, icono="bi-buildings", filtros=s.FILTROS_ANIO,
)
def clientes(periodo, filtros):
    w, p = where(filtros)
    agrupa = "GROUP BY c.ClienteId, c.ClienteNombre"
    ranking = sgo.filas(f"""
        SELECT RTRIM(c.ClienteNombre) AS label, COUNT(*) AS cantidad, SUM({IMPORTE}) AS monto_total, AVG({IMPORTE}) AS promedio,
               COUNT(DISTINCT a.AsignacionId) AS total_asignaciones
        {DESDE} {JOIN_CLI} WHERE {w} {agrupa} ORDER BY SUM({IMPORTE}) DESC""", p)
    ticket_global = sgo.valor(f"""SELECT AVG(promedio_cliente) AS ticket_promedio_global
        FROM (SELECT AVG({IMPORTE}) AS promedio_cliente {DESDE} WHERE {w} GROUP BY p.ClienteId) x""", p)
    heat = sgo.filas(f"""
        SELECT RTRIM(c.ClienteNombre) AS cliente, YEAR({FECHA}) AS anio, MONTH({FECHA}) AS mes, COUNT(*) AS cantidad,
               SUM({IMPORTE}) AS monto_total
        {DESDE} {JOIN_CLI} WHERE {w} AND {FECHA_VALIDA} AND YEAR({FECHA}) >= YEAR(GETDATE()) - 1
        GROUP BY c.ClienteId, c.ClienteNombre, YEAR({FECHA}), MONTH({FECHA})""", p)
    evol = sgo.filas(f"""
        WITH top5 AS (SELECT TOP 5 p.ClienteId {DESDE} WHERE {w} AND {FECHA} >= DATEADD(MONTH, -12, GETDATE())
                      GROUP BY p.ClienteId ORDER BY SUM({IMPORTE}) DESC)
        SELECT RTRIM(c.ClienteNombre) AS cliente, YEAR({FECHA}) AS anio, MONTH({FECHA}) AS mes, SUM({IMPORTE}) AS monto_total
        {DESDE} {JOIN_CLI} INNER JOIN top5 t ON t.ClienteId = p.ClienteId
        WHERE {w} AND {FECHA} >= DATEADD(MONTH, -12, GETDATE())
        GROUP BY c.ClienteId, c.ClienteNombre, YEAR({FECHA}), MONTH({FECHA}) ORDER BY anio, mes""", p + p)
    wc, pc = where(filtros, con_anio=False)
    comparativa = sgo.filas(f"""
        SELECT TOP 15 cliente AS label, anio_actual, anio_anterior,
               CASE WHEN anio_anterior > 0 THEN ((anio_actual - anio_anterior) * 100.0 / anio_anterior) ELSE 0 END AS variacion_porcentual
        FROM (SELECT RTRIM(c.ClienteNombre) AS cliente,
                     SUM(CASE WHEN YEAR({FECHA}) = YEAR(GETDATE()) THEN {IMPORTE} ELSE 0 END) AS anio_actual,
                     SUM(CASE WHEN YEAR({FECHA}) = YEAR(GETDATE()) - 1 THEN {IMPORTE} ELSE 0 END) AS anio_anterior
              {DESDE} {JOIN_CLI} WHERE {wc} AND YEAR({FECHA}) >= YEAR(GETDATE()) - 1 {agrupa}) x
        WHERE anio_actual > 0 OR anio_anterior > 0 ORDER BY anio_actual + anio_anterior DESC""", pc)

    top20 = ranking[:20]
    total_monto = total(ranking, "monto_total")
    top10 = total(ranking[:10], "monto_total")
    ratio = sorted(({"label": r["label"], "ratio": round(proporcion(r["cantidad"], r["total_asignaciones"]) / 100, 2)}
                    for r in ranking if num(r["total_asignaciones"]) >= 3), key=lambda r: -r["ratio"])[:15]
    meses_h = sorted({f"{int(num(r['anio']))}-{int(num(r['mes'])):02d}" for r in heat
                      if isinstance(r.get("anio"), (int, float)) or str(r.get("anio")).isdigit()})
    top_h = [r["label"] for r in ranking[:15]]
    celdas = []
    for r in heat:
        try:
            m = f"{int(num(r['anio']))}-{int(num(r['mes'])):02d}"
        except (ValueError, TypeError):
            continue
        if r["cliente"] in top_h and m in meses_h:
            celdas.append([meses_h.index(m), top_h.index(r["cliente"]), num(r["cantidad"])])
    clientes_evol = list(dict.fromkeys(r["cliente"] for r in evol))
    meses_e = sorted({f"{int(num(r['anio']))}-{int(num(r['mes'])):02d}" for r in evol
                      if isinstance(r.get("anio"), (int, float)) or str(r.get("anio")).isdigit()})
    series_e = {cl: [None] * len(meses_e) for cl in clientes_evol}
    for r in evol:
        try:
            series_e[r["cliente"]][meses_e.index(f"{int(num(r['anio']))}-{int(num(r['mes'])):02d}")] = num(r["monto_total"])
        except (ValueError, TypeError):
            pass
    anio = date.today().year

    secciones = [
        seccion(
            "Ranking de los 20 clientes con más gasto",
            [concentracion(top20, "monto_total", 3, "gasto del top 20")],
            g.ranking(etiquetas(top20), valores(top20, "monto_total"), "Monto", formato="fmt:pesos_k"),
            alto=g.alto_ranking(len(top20)),
            explicacion="Clientes por monto total de viáticos.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus viáticos.",
            tabla=tabla("Top 20", ["Cliente", "Viáticos", "Monto", "Promedio"],
                        [[r["label"], entero(r["cantidad"]), monto(r["monto_total"]), monto(r["promedio"])] for r in top20]),
        ),
        seccion(
            "Concentración del gasto (top 10 vs. resto)",
            [f"Los 10 clientes de mayor gasto concentran el {pct(proporcion(top10, total_monto))} del total."],
            g.torta([("Top 10 clientes", top10), ("Resto de clientes", total_monto - top10)], colores=[g.SERIES[0], g.NEUTRO]),
            explicacion="Qué parte del gasto total depende de los 10 clientes con más viáticos.",
        ),
        seccion(
            "Viáticos por asignación",
            [extremos(ratio, "label", "ratio", decimal, "más viáticos por asignación", "menos")],
            g.ranking([r["label"] for r in ratio], [r["ratio"] for r in ratio], "Viáticos por asignación", g.SERIES[1]),
            alto=g.alto_ranking(len(ratio)),
            explicacion="Cantidad de viáticos ÷ asignaciones con viáticos, para clientes con 3 asignaciones o más.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus viáticos.",
        ),
        seccion(
            "Evolución de los 5 clientes principales (últimos 12 meses)",
            [],
            g.lineas(meses_e, series_e, formato="fmt:pesos_k"),
            explicacion="Monto mensual de los 5 clientes con más gasto en el último año.",
        ),
        seccion(
            f"Comparativa {anio} vs. {anio - 1} (top 15)",
            [],
            g.columnas(etiquetas(comparativa), {str(anio - 1): valores(comparativa, "anio_anterior"),
                                                str(anio): valores(comparativa, "anio_actual")}, formato="fmt:pesos_k"),
            alto=360,
            explicacion="Gasto de cada cliente en el año actual y en el anterior. No usa el filtro de año.",
            detalle="cliente", ayuda_detalle="Hacé clic en un cliente para ver sus viáticos.",
        ),
        seccion(
            "Actividad por cliente y mes",
            ["Las celdas más oscuras son los meses con más viáticos de cada cliente."],
            g.mapa_calor(meses_h, top_h, celdas), alto=max(340, 30 * len(top_h) + 120),
            explicacion="Cantidad de viáticos por mes (columnas) de los 15 clientes con más gasto (filas), desde el año pasado.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total clientes", entero(len(ranking)), "con viáticos"),
            kpi("Cliente de mayor gasto", ranking[0]["label"] if ranking else "—",
                monto(ranking[0]["monto_total"]) if ranking else ""),
            kpi("Cliente más frecuente", max(ranking, key=lambda r: num(r["cantidad"]))["label"] if ranking else "—"),
            kpi("Ticket promedio", monto(ticket_global), "promedio de los promedios por cliente"),
        ],
        "conclusiones": [
            f"Los 10 clientes de mayor gasto concentran el {pct(proporcion(top10, total_monto))} de los viáticos.",
            f"{ranking[0]['label']} es el cliente de mayor gasto ({monto(ranking[0]['monto_total'])})." if ranking else "",
            extremos(ratio, "label", "ratio", decimal, "más viáticos por asignación", "menos"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué cliente aumentó más su gasto este año?", "¿El gasto está concentrado en pocos clientes?"],
        "contexto_ia": {"top20": top20, "comparativa": comparativa, "ratio": ratio},
    }


@catalogo.detalle("clientes")
def detalle_clientes(clave, valor, serie, periodo, filtros):
    filas = s.viaticos(filtros, "RTRIM(cl.ClienteNombre) = %s", [valor], con_anio=clave != "cliente" or serie not in
                       (str(date.today().year), str(date.today().year - 1)))
    return respuesta_detalle(f"Viáticos de {valor}", s.COLUMNAS_VIATICO, filas)
