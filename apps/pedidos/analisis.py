"""Análisis del módulo Pedidos."""
from collections import defaultdict

from apps.core import graficos as g
from apps.core.analisis import Catalogo
from apps.core.estadistica import pronostico, variacion_pct
from apps.core.utils import etiqueta_mes, formato_numero, formato_pct, siguientes_meses

from . import services

catalogo = Catalogo()

MESES_PERIODO = {"30": 3, "90": 6, "365": 12}


# --------------------------------------------------------------------------
# Descriptivo
# --------------------------------------------------------------------------
@catalogo.registrar(
    "descriptivo", "evolucion", "Evolución de pedidos",
    "Altas y cierres por mes, comparados con el mismo período del año anterior.",
)
def evolucion(periodo):
    meses, altas, cierres, _ = services.serie_mensual()
    n = MESES_PERIODO[periodo]
    m, a, c = meses[-n:], altas[-n:], cierres[-n:]
    a_ant = altas[-n - 12:-12]

    total_altas, total_cierres = sum(a), sum(c)
    var = variacion_pct(total_altas, sum(a_ant))
    pico = max(range(n), key=lambda i: a[i])
    abiertos = services.pedidos_abiertos()

    opcion = g.base(
        legend=g.leyenda(),
        xAxis=g.eje_categorias([etiqueta_mes(*x) for x in m]),
        yAxis=g.eje_valores(),
        series=[
            g.barras("Altas", a, g.SERIES[0]),
            g.barras("Cierres", c, g.SERIES[1]),
            g.linea("Altas año anterior", a_ant, g.NEUTRO,
                    lineStyle={"width": 2, "type": "dashed", "color": g.NEUTRO}, symbol="none"),
        ],
    )

    return {
        "kpis": [
            {"label": "Altas en el período", "valor": total_altas,
             "detalle": f"{formato_pct(var, signo=True)} contra el año anterior"},
            {"label": "Cierres en el período", "valor": total_cierres,
             "detalle": f"{round(total_cierres / total_altas * 100) if total_altas else 0}% de las altas"},
            {"label": "Abiertos hoy", "valor": len(abiertos),
             "detalle": f"{sum(p['pendientes'] for p in abiertos)} vacantes pendientes"},
            {"label": "Vencidos hoy", "valor": len(services.vencidos()), "alerta": True,
             "detalle": "pasaron la fecha tope"},
        ],
        "grafico": opcion,
        "lectura": [
            f"El mes con más altas fue {etiqueta_mes(*m[pico])}, con {a[pico]} pedidos.",
            f"Las altas {'crecieron' if var >= 0 else 'bajaron'} {formato_pct(abs(var))} respecto al mismo período del año pasado.",
            "Cuando los cierres quedan por debajo de las altas varios meses seguidos, se acumulan pedidos abiertos."
            if total_cierres < total_altas else
            "Los cierres acompañan el ritmo de las altas: la cartera abierta no está creciendo.",
        ],
        "sugerencias": [
            "¿Qué meses tienen más demanda en el año?",
            "¿Estamos cerrando al mismo ritmo que entran pedidos?",
        ],
        "contexto_ia": {"meses": [etiqueta_mes(*x) for x in m], "altas": a, "cierres": c,
                        "altas_anio_anterior": a_ant},
    }


# --------------------------------------------------------------------------
# Diagnóstico
# --------------------------------------------------------------------------
@catalogo.registrar(
    "diagnostico", "vencimientos", "Dónde se vencen los pedidos",
    "Porcentaje de pedidos que pasaron la fecha tope en los últimos 12 meses, cruzando cliente y puesto.",
    usa_periodo=False,
)
def vencimientos(periodo):
    datos = services.cumplimiento_cliente_puesto()
    clientes = sorted({c for c, _ in datos})
    puestos = sorted({p for _, p in datos})

    celdas = []
    for (cliente, puesto), (total, venc) in datos.items():
        pct = round(venc / total * 100)
        celdas.append({"value": [puestos.index(puesto), clientes.index(cliente), pct],
                       "label": {"color": "#fff" if pct >= 30 else g.TINTA}})

    tot = sum(t for t, _ in datos.values())
    ven = sum(v for _, v in datos.values())
    tasa = round(ven / tot * 100)

    por_cliente, por_puesto = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for (c, p), (t, v) in datos.items():
        por_cliente[c][0] += t; por_cliente[c][1] += v
        por_puesto[p][0] += t; por_puesto[p][1] += v
    tasa_c = {c: round(v / t * 100) for c, (t, v) in por_cliente.items()}
    tasa_p = {p: round(v / t * 100) for p, (t, v) in por_puesto.items()}
    peor_c = max(tasa_c, key=tasa_c.get)
    peor_p = max(tasa_p, key=tasa_p.get)
    peores = sorted(datos.items(), key=lambda x: x[1][1] / x[1][0], reverse=True)

    opcion = g.base(
        tooltip={"trigger": "item", "confine": True},
        grid={"left": 8, "right": 16, "top": 8, "bottom": 56, "containLabel": True},
        xAxis=g.eje_categorias(puestos, splitArea={"show": False}, axisLabel={"interval": 0, "rotate": 25, "color": g.TINTA_SUAVE}),
        yAxis=g.eje_categorias(clientes),
        visualMap={"min": 0, "max": 50, "calculable": False, "orient": "horizontal",
                   "left": "center", "bottom": 0, "itemWidth": 12, "text": ["50%", "0%"],
                   "inRange": {"color": g.NARANJA}, "textStyle": {"color": g.TINTA_SUAVE}},
        series=[{
            "name": "% vencidos", "type": "heatmap", "data": celdas,
            "label": {"show": True, "formatter": "{@[2]}%", "fontWeight": 600},
            "itemStyle": {"borderColor": "#fff", "borderWidth": 2, "borderRadius": 4},
            "emphasis": {"itemStyle": {"borderColor": g.TINTA}},
        }],
    )

    return {
        "kpis": [
            {"label": "Pedidos vencidos", "valor": f"{tasa}%", "alerta": tasa > 20,
             "detalle": f"{ven} de {tot} en los últimos 12 meses"},
            {"label": "Cliente más afectado", "valor": peor_c, "detalle": f"{tasa_c[peor_c]}% de sus pedidos"},
            {"label": "Puesto más difícil", "valor": peor_p, "detalle": f"{tasa_p[peor_p]}% vencidos"},
            {"label": "Combinaciones sobre 30%", "valor": sum(1 for _, (t, v) in datos.items() if v / t > .3),
             "detalle": "cliente + puesto"},
        ],
        "grafico": opcion,
        "grafico_alto": 420,
        "lectura": [
            f"{peores[0][0][1]} para {peores[0][0][0]} es la combinación con más vencimientos "
            f"({round(peores[0][1][1] / peores[0][1][0] * 100)}%).",
            f"El problema está más en el puesto que en el cliente: {peor_p} se vence {tasa_p[peor_p]}% "
            f"contra {tasa}% del promedio." if tasa_p[peor_p] - tasa > tasa_c[peor_c] - tasa else
            f"El problema está más en el cliente que en el puesto: {peor_c} se vence {tasa_c[peor_c]}% "
            f"contra {tasa}% del promedio.",
            "Las celdas vacías son combinaciones sin pedidos en el período.",
        ],
        "tabla": {
            "titulo": "Combinaciones con más vencimientos",
            "columnas": ["Cliente", "Puesto", "Pedidos", "Vencidos", "%"],
            "filas": [[c, p, t, v, f"{round(v / t * 100)}%"] for (c, p), (t, v) in peores[:6]],
        },
        "sugerencias": [
            "¿Por qué se vencen tanto los choferes?",
            "¿Qué tienen en común las combinaciones más críticas?",
        ],
        "contexto_ia": {"tasa_global": tasa, "por_cliente": tasa_c, "por_puesto": tasa_p},
    }


# --------------------------------------------------------------------------
# Predictivo
# --------------------------------------------------------------------------
@catalogo.registrar(
    "predictivo", "demanda", "Demanda esperada",
    "Proyección de pedidos para los próximos 3 meses según tendencia y estacionalidad.",
    usa_periodo=False,
)
def demanda(periodo):
    meses, altas, _, vacantes = services.serie_mensual()
    # El mes actual está en curso: se proyecta con los meses completos
    hist, meses_hist, vac_hist = altas[:-1], meses[:-1], vacantes[:-1]
    p = pronostico(hist, pasos=3)
    pv = pronostico(vac_hist, pasos=3)
    futuros = siguientes_meses(meses_hist[-1], 3)

    ver = 12
    opcion = g.serie_pronostico(
        hist[-ver:], p,
        [etiqueta_mes(*x) for x in meses_hist[-ver:]],
        [etiqueta_mes(*x) for x in futuros],
        nombre="Pedidos reales",
    )
    prox = round(p["valores"][0])
    mismo_mes = hist[-12]

    return {
        "kpis": [
            {"label": f"Pedidos esperados en {etiqueta_mes(*futuros[0])}", "valor": prox,
             "detalle": f"entre {round(p['inferior'][0])} y {round(p['superior'][0])}"},
            {"label": "Próximos 3 meses", "valor": round(sum(p["valores"])),
             "detalle": f"{formato_numero(round(sum(pv['valores'])))} vacantes estimadas"},
            {"label": "Tendencia", "valor": f"{'+' if p['pendiente'] >= 0 else ''}{p['pendiente']:.1f}".replace(".", ","),
             "detalle": "pedidos más por mes"},
            {"label": "Contra el año anterior", "valor": formato_pct(variacion_pct(prox, mismo_mes), signo=True, decimales=0),
             "detalle": f"{etiqueta_mes(*meses_hist[-12])}: {mismo_mes} pedidos"},
        ],
        "grafico": opcion,
        "lectura": [
            f"Se esperan unos {prox} pedidos en {etiqueta_mes(*futuros[0])}; con 80% de probabilidad "
            f"van a estar entre {round(p['inferior'][0])} y {round(p['superior'][0])}.",
            f"La demanda viene {'creciendo' if p['pendiente'] > 0 else 'bajando'} "
            f"{abs(p['pendiente']):.1f} pedidos por mes".replace(".", ",") + f", con picos repetidos en los mismos meses de cada año.",
            "La proyección usa los últimos 23 meses completos. El mes en curso no se toma porque todavía no terminó.",
        ],
        "tabla": {
            "titulo": "Proyección mes a mes",
            "columnas": ["Mes", "Pedidos esperados", "Mínimo", "Máximo", "Vacantes estimadas"],
            "filas": [[etiqueta_mes(*f), round(v), round(lo), round(hi), round(vv)]
                      for f, v, lo, hi, vv in zip(futuros, p["valores"], p["inferior"], p["superior"], pv["valores"])],
        },
        "sugerencias": [
            "¿Cuántos selectores vamos a necesitar el mes que viene?",
            "¿Qué tan confiable es esta proyección?",
        ],
        "contexto_ia": {"proyeccion": dict(zip([etiqueta_mes(*f) for f in futuros], p["valores"])),
                        "tendencia_mensual": round(p["pendiente"], 1)},
    }


# --------------------------------------------------------------------------
# Prescriptivo
# --------------------------------------------------------------------------
def _riesgo(p):
    """Puntaje 0-100: cuanto más cerca (o pasado) del tope y más vacantes pendientes, mayor."""
    tiempo = max(0, min(1, (10 - p["dias_a_tope"]) / 30))
    faltante = p["pendientes"] / p["vacantes"] if p["vacantes"] else 0
    peso_cliente = {"A": 1, "B": .85, "C": .7}[p["ranking"]]
    return round((tiempo * .6 + faltante * .4) * peso_cliente * 100)


def _accion(p):
    if p["dias_a_tope"] < 0:
        return ("alta", f"Pedido {p['numero']} · {p['cliente']} ({p['puesto']})",
                f"Venció hace {-p['dias_a_tope']} días con {p['pendientes']} de {p['vacantes']} vacantes sin cubrir. "
                "Llamar al cliente para acordar nueva fecha y asignar un segundo selector.")
    if p["dias_a_tope"] <= 5:
        return ("alta" if p["pendientes"] > 1 else "media",
                f"Pedido {p['numero']} · {p['cliente']} ({p['puesto']})",
                f"Vence en {p['dias_a_tope']} {'día' if p['dias_a_tope'] == 1 else 'días'} y faltan {p['pendientes']} vacantes. "
                "Revisar candidatos en base y priorizar entrevistas esta semana.")
    return ("baja", f"Pedido {p['numero']} · {p['cliente']} ({p['puesto']})",
            f"Faltan {p['dias_a_tope']} días y {p['pendientes']} vacantes. Seguir el ritmo actual.")


@catalogo.registrar(
    "prescriptivo", "priorizar", "Pedidos a priorizar",
    "Qué pedidos atender primero según cercanía al vencimiento y vacantes pendientes.",
    usa_periodo=False,
)
def priorizar(periodo):
    abiertos = sorted(services.pedidos_abiertos(), key=_riesgo, reverse=True)
    acciones = []
    for p in abiertos:
        prioridad, titulo, detalle = _accion(p)
        acciones.append({"prioridad": prioridad, "titulo": titulo, "detalle": detalle})

    nombres = {"alta": "Prioridad alta", "media": "Prioridad media", "baja": "Prioridad baja"}
    colores = {"alta": g.ESTADO["critico"], "media": g.ESTADO["atencion"], "baja": g.ESTADO["bien"]}
    series = []
    for pr in ("alta", "media", "baja"):
        series.append({
            "name": nombres[pr], "type": "scatter", "symbolSize": 18,
            "itemStyle": {"color": colores[pr], "borderColor": "#fff", "borderWidth": 2},
            "data": [[p["dias_a_tope"], p["pendientes"], p["numero"], p["cliente"], _riesgo(p)]
                     for p in abiertos if _accion(p)[0] == pr],
            "label": {"show": True, "formatter": "{@[2]}", "position": "right", "color": g.TINTA_SUAVE, "fontSize": 11},
            "labelLayout": {"moveOverlap": "shiftY"},
        })
    minimo = min(p["dias_a_tope"] for p in abiertos) - 5
    series[0]["markArea"] = {"silent": True, "itemStyle": {"color": "rgba(208,59,59,.06)"},
                             "label": {"color": g.ESTADO["critico"], "position": "insideTopLeft"},
                             "data": [[{"name": "Vencidos", "xAxis": minimo}, {"xAxis": 0}]]}
    series[0]["markLine"] = {"silent": True, "symbol": "none", "lineStyle": {"color": g.EJE, "type": "dashed"},
                             "label": {"show": False}, "data": [{"xAxis": 0}]}

    opcion = g.base(
        legend=g.leyenda(),
        tooltip={"trigger": "item", "confine": True,
                 "formatter": "Pedido {@[2]} · {@[3]}<br>Días a la fecha tope: {@[0]}<br>"
                              "Vacantes pendientes: {@[1]}<br>Riesgo: {@[4]}/100"},
        grid={"left": 36, "right": 40, "top": 40, "bottom": 40, "containLabel": True},
        xAxis=g.eje_valores(name="Días hasta la fecha tope", nameLocation="middle", nameGap=30,
                            splitLine={"show": False}, min=minimo),
        yAxis=g.eje_valores(name="Vacantes pendientes", nameLocation="middle", nameGap=30, minInterval=1),
        series=series,
    )

    altas = [a for a in acciones if a["prioridad"] == "alta"]
    return {
        "kpis": [
            {"label": "Requieren acción hoy", "valor": len(altas), "alerta": bool(altas),
             "detalle": "prioridad alta"},
            {"label": "Vacantes en riesgo", "valor": sum(p["pendientes"] for p in abiertos if _riesgo(p) >= 50),
             "detalle": "en pedidos con riesgo ≥ 50"},
            {"label": "Pedidos abiertos", "valor": len(abiertos), "detalle": "ordenados por riesgo"},
            {"label": "Riesgo promedio", "valor": round(sum(map(_riesgo, abiertos)) / len(abiertos)),
             "detalle": "sobre 100"},
        ],
        "grafico": opcion,
        "lectura": [
            "Arriba a la izquierda están los pedidos más urgentes: vencidos o por vencer, con muchas vacantes sin cubrir.",
            f"Empezar por el pedido {abiertos[0]['numero']} de {abiertos[0]['cliente']}: es el de mayor riesgo ({_riesgo(abiertos[0])}/100).",
            "El riesgo combina días a la fecha tope (60%), vacantes pendientes (40%) y el ranking del cliente.",
        ],
        "acciones": acciones[:6],
        "sugerencias": [
            "¿A quién asigno el pedido más urgente?",
            "Redactame un mail al cliente para pedir más plazo",
        ],
        "contexto_ia": {"pedidos": [{"numero": p["numero"], "cliente": p["cliente"], "puesto": p["puesto"],
                                     "dias_a_tope": p["dias_a_tope"], "pendientes": p["pendientes"],
                                     "riesgo": _riesgo(p)} for p in abiertos]},
    }
