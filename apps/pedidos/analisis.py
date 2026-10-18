"""Análisis del módulo Pedidos."""
from collections import defaultdict

from apps.core import graficos as g
from apps.core.analisis import Catalogo, seccion
from apps.core.estadistica import pronostico, variacion_pct
from apps.core.utils import (
    etiqueta_mes, formato_numero, formato_pct, siguientes_meses,
)

from . import services

catalogo = Catalogo()

MESES_PERIODO = {"30": 3, "90": 6, "365": 12}

# Vacantes que un selector cubre en promedio por mes (para estimar capacidad)
VACANTES_POR_SELECTOR = 28
SELECTORES_ACTUALES = 6


def _decimal(valor):
    return f"{valor:.1f}".replace(".", ",")


# ==========================================================================
# Demanda y capacidad
# ==========================================================================
@catalogo.registrar(
    "demanda", "Demanda y capacidad",
    "Cómo evolucionan los pedidos, qué puestos los explican, cuántos se esperan y qué capacidad de selección hace falta.",
    icono="bi-graph-up-arrow",
)
def demanda(periodo):
    meses, altas, cierres, vacantes = services.serie_mensual()
    n = MESES_PERIODO[periodo]

    # --- Qué pasó (solo meses completos: el mes en curso todavía no terminó) ---
    m, a, c = meses[-n - 1:-1], altas[-n - 1:-1], cierres[-n - 1:-1]
    a_ant = altas[-n - 13:-13]
    var = variacion_pct(sum(a), sum(a_ant))
    pico = max(range(n), key=lambda i: a[i])
    grafico_evolucion = g.base(
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
    acumulado = sum(a) - sum(c)

    # --- Por qué: qué puestos mueven la demanda ---------------------------
    por_puesto = defaultdict(int)
    for (_, puesto), (total, _) in services.cumplimiento_cliente_puesto().items():
        por_puesto[puesto] += total
    puestos = sorted(por_puesto.items(), key=lambda x: -x[1])
    total_p = sum(por_puesto.values())
    grafico_puestos = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        grid={"left": 8, "right": 48, "top": 8, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores(),
        yAxis=g.eje_categorias([p for p, _ in puestos], inverse=True),
        series=[g.barras("Pedidos 12 meses", [v for _, v in puestos], g.SERIES[0],
                         itemStyle={"color": g.SERIES[0], "borderRadius": [0, 4, 4, 0]}, barMaxWidth=22,
                         label={"show": True, "position": "right", "color": g.TINTA_SUAVE})],
    )
    top2 = sum(v for _, v in puestos[:2])

    # --- Qué se espera ----------------------------------------------------
    hist, meses_hist, vac_hist = altas[:-1], meses[:-1], vacantes[:-1]
    p = pronostico(hist, pasos=3)
    pv = pronostico(vac_hist, pasos=3)
    futuros = siguientes_meses(meses_hist[-1], 3)
    grafico_pronostico = g.serie_pronostico(
        hist[-12:], p, [etiqueta_mes(*x) for x in meses_hist[-12:]], [etiqueta_mes(*x) for x in futuros],
        nombre="Pedidos reales",
    )
    prox = round(p["valores"][0])

    # --- Qué hacer: capacidad ---------------------------------------------
    necesarios = [v / VACANTES_POR_SELECTOR for v in pv["valores"]]
    pico_nec = max(necesarios)
    faltan = max(0, round(pico_nec + .49) - SELECTORES_ACTUALES)
    acciones = []
    if faltan:
        mes_pico = etiqueta_mes(*futuros[necesarios.index(pico_nec)])
        acciones.append({"prioridad": "alta", "titulo": f"Sumar {faltan} selector{'es' if faltan > 1 else ''} para {mes_pico}",
                         "detalle": f"Se esperan {round(max(pv['valores']))} vacantes y hoy el equipo cubre unas "
                                    f"{SELECTORES_ACTUALES * VACANTES_POR_SELECTOR} por mes. Reforzar con selectores "
                                    "temporales o redistribuir desde otras sucursales."})
    else:
        acciones.append({"prioridad": "baja", "titulo": "La capacidad actual alcanza",
                         "detalle": f"El equipo de {SELECTORES_ACTUALES} selectores cubre la demanda esperada."})
    acciones.append({"prioridad": "media", "titulo": f"Armar base de candidatos para {puestos[0][0].lower()} y {puestos[1][0].lower()}",
                     "detalle": f"Concentran el {round(top2 / total_p * 100)}% de los pedidos. Tener candidatos "
                                "preseleccionados acorta el tiempo de cierre cuando llega el pico."})
    if acumulado > 0:
        acciones.append({"prioridad": "media", "titulo": "Reducir la cartera abierta",
                         "detalle": f"En el período entraron {acumulado} pedidos más de los que se cerraron. "
                                    "Revisar los abiertos más antiguos y cerrar o cancelar los que ya no corren."})

    return {
        "kpis": [
            {"label": "Altas en el período", "valor": sum(a),
             "detalle": f"{formato_pct(var, signo=True)} contra el año anterior"},
            {"label": f"Esperados en {etiqueta_mes(*futuros[0])}", "valor": prox,
             "detalle": f"entre {round(p['inferior'][0])} y {round(p['superior'][0])}"},
            {"label": "Vacantes próximos 3 meses", "valor": formato_numero(round(sum(pv["valores"]))),
             "detalle": "estimadas"},
            {"label": "Selectores necesarios", "valor": _decimal(pico_nec), "alerta": faltan > 0,
             "detalle": f"en el mes pico (hoy hay {SELECTORES_ACTUALES})"},
        ],
        "conclusiones": [
            f"Las altas {'crecieron' if var >= 0 else 'bajaron'} {formato_pct(abs(var))} contra el mismo período del año pasado.",
            f"{puestos[0][0]} y {puestos[1][0]} explican el {round(top2 / total_p * 100)}% de la demanda.",
            f"Para {etiqueta_mes(*futuros[0])} se esperan unos {prox} pedidos, con la tendencia "
            f"{'en suba' if p['pendiente'] > 0 else 'en baja'}.",
            f"Hace{'n' if faltan > 1 else ''} falta {faltan} selector{'es' if faltan > 1 else ''} más para cubrir el pico." if faltan
            else "La capacidad actual del equipo alcanza para la demanda esperada.",
        ],
        "secciones": [
            seccion("Cómo evolucionó la demanda", grafico=grafico_evolucion, lectura=[
                f"El mes con más altas fue {etiqueta_mes(*m[pico])}, con {a[pico]} pedidos.",
                f"Entraron {acumulado} pedidos más de los que se cerraron: la cartera abierta crece." if acumulado > 0
                else "Los cierres acompañan a las altas: la cartera abierta no crece.",
                "La línea punteada muestra las altas del mismo período del año anterior.",
            ]),
            seccion("Qué puestos explican la demanda", grafico=grafico_puestos, alto=260,
                    descripcion="Pedidos de los últimos 12 meses por puesto.", lectura=[
                f"{puestos[0][0]} es el puesto más pedido: {round(puestos[0][1] / total_p * 100)}% del total.",
                f"Los dos primeros puestos concentran {round(top2 / total_p * 100)}% de los pedidos.",
            ]),
            seccion("Cuántos pedidos se esperan", grafico=grafico_pronostico, lectura=[
                f"Se esperan unos {prox} pedidos en {etiqueta_mes(*futuros[0])}; con 80% de probabilidad "
                f"van a estar entre {round(p['inferior'][0])} y {round(p['superior'][0])}.",
                f"La tendencia es de {_decimal(abs(p['pendiente']))} pedidos {'más' if p['pendiente'] > 0 else 'menos'} por mes, "
                "con picos que se repiten en los mismos meses de cada año.",
                "El mes en curso no se usa para proyectar porque todavía no terminó.",
            ], tabla={
                "titulo": "Proyección mes a mes",
                "columnas": ["Mes", "Pedidos", "Mínimo", "Máximo", "Vacantes", "Selectores necesarios"],
                "filas": [[etiqueta_mes(*f), round(v), round(lo), round(hi), round(vv), _decimal(nec)]
                          for f, v, lo, hi, vv, nec in zip(futuros, p["valores"], p["inferior"], p["superior"],
                                                           pv["valores"], necesarios)],
            }),
            seccion("Qué capacidad hace falta", acciones=acciones, lectura=[
                f"Cada selector cubre en promedio {VACANTES_POR_SELECTOR} vacantes por mes; con "
                f"{SELECTORES_ACTUALES} selectores, la capacidad es de {SELECTORES_ACTUALES * VACANTES_POR_SELECTOR} vacantes.",
                f"En el mes pico se esperan {round(max(pv['valores']))} vacantes.",
            ]),
        ],
        "sugerencias": [
            "¿Cuántos selectores vamos a necesitar el mes que viene?",
            "¿Qué tan confiable es esta proyección?",
            "¿Qué meses tienen más demanda en el año?",
        ],
        "contexto_ia": {"altas": dict(zip([etiqueta_mes(*x) for x in m], a)),
                        "por_puesto": dict(puestos),
                        "proyeccion": dict(zip([etiqueta_mes(*f) for f in futuros], p["valores"])),
                        "selectores_actuales": SELECTORES_ACTUALES, "selectores_pico": round(pico_nec, 1)},
    }


# ==========================================================================
# Vencimientos y prioridades
# ==========================================================================
def _riesgo(p):
    """Puntaje 0-100: cuanto más cerca (o pasado) del tope y más vacantes pendientes, mayor."""
    tiempo = max(0, min(1, (10 - p["dias_a_tope"]) / 30))
    faltante = p["pendientes"] / p["vacantes"] if p["vacantes"] else 0
    peso_cliente = {"A": 1, "B": .85, "C": .7}[p["ranking"]]
    return round((tiempo * .6 + faltante * .4) * peso_cliente * 100)


def _accion(p):
    titulo = f"Pedido {p['numero']} · {p['cliente']} ({p['puesto']})"
    dias = p["dias_a_tope"]
    if dias < 0:
        return ("alta", titulo,
                f"Venció hace {-dias} {'día' if dias == -1 else 'días'} con {p['pendientes']} de {p['vacantes']} "
                "vacantes sin cubrir. Llamar al cliente para acordar nueva fecha y asignar un segundo selector.")
    if dias <= 5:
        return ("alta" if p["pendientes"] > 1 else "media", titulo,
                f"Vence en {dias} {'día' if dias == 1 else 'días'} y faltan {p['pendientes']} vacantes. "
                "Revisar candidatos en base y priorizar entrevistas esta semana.")
    return ("baja", titulo, f"Faltan {dias} días y {p['pendientes']} vacantes. Seguir el ritmo actual.")


@catalogo.registrar(
    "vencimientos", "Vencimientos y prioridades",
    "Dónde y por qué se vencen los pedidos, cuáles están en riesgo hoy y en qué orden atenderlos.",
    usa_periodo=False, icono="bi-alarm",
)
def vencimientos(periodo):
    # --- Por qué se vencen ------------------------------------------------
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

    grafico_calor = g.base(
        tooltip={"trigger": "item", "confine": True},
        grid={"left": 8, "right": 16, "top": 8, "bottom": 56, "containLabel": True},
        xAxis=g.eje_categorias(puestos, axisLabel={"interval": 0, "rotate": 25, "color": g.TINTA_SUAVE}),
        yAxis=g.eje_categorias(clientes),
        visualMap={"min": 0, "max": 50, "calculable": False, "orient": "horizontal", "left": "center",
                   "bottom": 0, "itemWidth": 12, "text": ["50%", "0%"], "inRange": {"color": g.NARANJA},
                   "textStyle": {"color": g.TINTA_SUAVE}},
        series=[{"name": "% vencidos", "type": "heatmap", "data": celdas,
                 "label": {"show": True, "formatter": "{@[2]}%", "fontWeight": 600},
                 "itemStyle": {"borderColor": "#fff", "borderWidth": 2, "borderRadius": 4}}],
    )
    causa_puesto = tasa_p[peor_p] - tasa > tasa_c[peor_c] - tasa

    # --- Qué está en riesgo hoy y qué hacer --------------------------------
    abiertos = sorted(services.pedidos_abiertos(), key=_riesgo, reverse=True)
    acciones = [dict(zip(("prioridad", "titulo", "detalle"), _accion(p))) for p in abiertos]
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
    grafico_riesgo = g.base(
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
    urgentes = [a for a in acciones if a["prioridad"] == "alta"]
    vencidos_hoy = [p for p in abiertos if p["dias_a_tope"] < 0]
    por_vencer = [p for p in abiertos if 0 <= p["dias_a_tope"] <= 7]
    # Si se mantiene la tasa histórica, cuántos de los que vencen esta semana se van a vencer sin cubrir
    esperados = round(len(por_vencer) * tasa / 100 + .49) if por_vencer else 0

    return {
        "kpis": [
            {"label": "Tasa de vencimiento", "valor": f"{tasa}%", "alerta": tasa > 20,
             "detalle": f"{ven} de {tot} pedidos en 12 meses"},
            {"label": "Vencidos hoy", "valor": len(vencidos_hoy), "alerta": bool(vencidos_hoy),
             "detalle": f"{sum(p['pendientes'] for p in vencidos_hoy)} vacantes sin cubrir"},
            {"label": "Vencen en 7 días", "valor": len(por_vencer),
             "detalle": f"se esperan {esperados} vencidos si no se actúa"},
            {"label": "Requieren acción hoy", "valor": len(urgentes), "alerta": bool(urgentes),
             "detalle": "prioridad alta"},
        ],
        "conclusiones": [
            f"El {tasa}% de los pedidos pasa la fecha tope antes de cubrirse.",
            (f"El problema está más en el puesto que en el cliente: {peor_p} se vence {tasa_p[peor_p]}%." if causa_puesto
             else f"El problema está más en el cliente que en el puesto: {peor_c} se vence {tasa_c[peor_c]}%."),
            f"Hoy hay {len(vencidos_hoy)} pedidos vencidos y {len(por_vencer)} que vencen esta semana.",
            f"Empezar por el pedido {abiertos[0]['numero']} de {abiertos[0]['cliente']}: es el de mayor riesgo.",
        ],
        "secciones": [
            seccion("Dónde se vencen los pedidos", grafico=grafico_calor, alto=420,
                    descripcion="Porcentaje de pedidos de los últimos 12 meses que pasaron la fecha tope, por cliente y puesto.",
                    lectura=[
                        f"{peores[0][0][1]} para {peores[0][0][0]} es la combinación más crítica "
                        f"({round(peores[0][1][1] / peores[0][1][0] * 100)}% vencidos).",
                        f"{peor_p} es el puesto más difícil ({tasa_p[peor_p]}%) y {peor_c} el cliente con más "
                        f"vencimientos ({tasa_c[peor_c]}%), contra {tasa}% del promedio.",
                        "Las celdas vacías son combinaciones sin pedidos en el período.",
                    ]),
            seccion("Qué pedidos atender primero", grafico=grafico_riesgo, alto=380, acciones=acciones[:6],
                    descripcion="Pedidos abiertos hoy según días a la fecha tope y vacantes pendientes.",
                    lectura=[
                        "Arriba a la izquierda están los más urgentes: vencidos o por vencer y con muchas vacantes sin cubrir.",
                        "El riesgo combina días a la fecha tope (60%), vacantes pendientes (40%) y el ranking del cliente.",
                    ]),
        ],
        "sugerencias": [
            "¿Por qué se vencen tanto los choferes?",
            "¿A quién asigno el pedido más urgente?",
            "Redactame un mail al cliente para pedir más plazo",
        ],
        "contexto_ia": {"tasa_global": tasa, "por_cliente": tasa_c, "por_puesto": tasa_p,
                        "pedidos_abiertos": [{"numero": p["numero"], "cliente": p["cliente"], "puesto": p["puesto"],
                                              "dias_a_tope": p["dias_a_tope"], "pendientes": p["pendientes"],
                                              "riesgo": _riesgo(p)} for p in abiertos]},
    }
