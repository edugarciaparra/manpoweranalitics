"""Análisis del módulo Facturación."""
from collections import defaultdict

from apps.core import graficos as g
from apps.core.analisis import Catalogo, seccion
from apps.core.estadistica import pronostico, regresion_lineal, variacion_pct
from apps.core.utils import (
    etiqueta_mes, formato_millones, formato_pct, formato_pesos, siguientes_meses,
)

from . import services

catalogo = Catalogo()

MESES_PERIODO = {"30": 1, "90": 3, "365": 12}


def _texto_periodo(n):
    return "el último mes" if n == 1 else f"los últimos {n} meses"


# ==========================================================================
# Evolución y proyección de ingresos
# ==========================================================================
@catalogo.registrar(
    "ingresos", "Evolución y proyección de ingresos",
    "Cómo vienen los ingresos, qué clientes explican la variación y cuánto se espera facturar.",
    icono="bi-cash-stack",
)
def ingresos(periodo):
    n = MESES_PERIODO[periodo]
    meses, datos = services.facturacion_mensual()
    _, total = services.total_mensual()

    # --- Qué pasó ---------------------------------------------------------
    ver = 12
    grafico_evolucion = g.base(
        legend=g.leyenda(),
        tooltip={"trigger": "axis", "confine": True, "valueFormatter": "fmt:pesos"},
        xAxis=g.eje_categorias([etiqueta_mes(*m) for m in meses[-ver:]]),
        yAxis=g.eje_valores("fmt:pesos_k", min=round(min(total) * .8, -5)),
        series=[
            g.barras("Facturado", [round(v) for v in total[-ver:]], g.SERIES[0]),
            g.linea("Año anterior", [round(v) for v in total[-2 * ver:-ver]], g.NEUTRO,
                    lineStyle={"width": 2, "type": "dashed", "color": g.NEUTRO}, symbol="none"),
        ],
    )
    ultimos12, anteriores12 = sum(total[-12:]), sum(total[-24:-12])
    mejor_mes = max(range(ver), key=lambda i: total[-ver:][i])

    # --- Por qué: puente de variación por cliente --------------------------
    actual = {c: sum(v[-n:]) for c, v in datos.items()}
    anterior = {c: sum(v[-2 * n:-n]) for c, v in datos.items()}
    deltas = sorted(((c, actual[c] - anterior[c]) for c in datos), key=lambda x: -x[1])
    tot_ant, tot_act = sum(anterior.values()), sum(actual.values())
    etiquetas = ["Período anterior"] + [c for c, _ in deltas] + ["Período actual"]
    base_inv, subida, bajada, acumulado = [0], [None], [None], tot_ant
    for _, d in deltas:
        if d >= 0:
            base_inv.append(acumulado); subida.append(d); bajada.append(None)
        else:
            base_inv.append(acumulado + d); subida.append(None); bajada.append(-d)
        acumulado += d
    base_inv.append(0)
    grafico_puente = g.base(
        legend=g.leyenda(data=["Total", "Sube", "Baja"]),
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pesos"},
        xAxis=g.eje_categorias(etiquetas, axisLabel={"interval": 0, "rotate": 35, "color": g.TINTA_SUAVE}),
        yAxis=g.eje_valores("fmt:pesos_k", min=round(min(tot_ant, tot_act) * .85, -5)),
        series=[
            {"name": "_base", "type": "bar", "stack": "w", "data": base_inv, "silent": True,
             "itemStyle": {"color": "transparent"}, "tooltip": {"show": False}},
            g.barras("Total", [tot_ant] + [None] * len(deltas) + [tot_act], g.NEUTRO, stack="w"),
            g.barras("Sube", subida, g.POSITIVO, stack="w"),
            g.barras("Baja", bajada, g.NEGATIVO, stack="w"),
        ],
    )
    var = variacion_pct(tot_act, tot_ant)
    sube, baja = deltas[0], deltas[-1]

    # --- Qué se espera ----------------------------------------------------
    p = pronostico(total, pasos=3)
    futuros = siguientes_meses(meses[-1], 3)
    grafico_pronostico = g.serie_pronostico(
        [round(v) for v in total[-12:]], p, [etiqueta_mes(*m) for m in meses[-12:]],
        [etiqueta_mes(*m) for m in futuros], nombre="Facturado", formato="fmt:pesos",
    )
    grafico_pronostico["yAxis"]["axisLabel"]["formatter"] = "fmt:pesos_k"
    grafico_pronostico["yAxis"]["min"] = round(min(total[-12:]) * .8, -5)
    trimestre = sum(p["valores"])
    trimestre_ant = sum(total[-12:-9])
    var_trim = variacion_pct(trimestre, trimestre_ant)

    # --- Qué hacer --------------------------------------------------------
    acciones = []
    if baja[1] < 0:
        acciones.append({"prioridad": "alta", "titulo": f"Revisar la cuenta de {baja[0]}",
                         "detalle": f"Restó {formato_pesos(-baja[1])} contra el período anterior. "
                                    "Confirmar si es un cambio puntual o una pérdida de servicios."})
    acciones.append({"prioridad": "media", "titulo": f"Asegurar el pico de {etiqueta_mes(*futuros[p['valores'].index(max(p['valores']))])}",
                     "detalle": f"Es el mes con más facturación esperada ({formato_millones(max(p['valores']))}). "
                                "Confirmar con los clientes principales los pedidos de temporada con anticipación."})
    if sube[1] > 0:
        acciones.append({"prioridad": "baja", "titulo": f"Aprovechar el crecimiento de {sube[0]}",
                         "detalle": f"Sumó {formato_pesos(sube[1])}. Explorar nuevos puestos o sedes con ese cliente."})

    return {
        "kpis": [
            {"label": "Facturado", "valor": formato_millones(tot_act), "detalle": _texto_periodo(n)},
            {"label": "Variación", "valor": formato_pct(var, signo=True), "alerta": var < 0,
             "detalle": "contra el período anterior"},
            {"label": f"Esperado en {etiqueta_mes(*futuros[0])}", "valor": formato_millones(p["valores"][0]),
             "detalle": f"entre {formato_millones(p['inferior'][0])} y {formato_millones(p['superior'][0])}"},
            {"label": "Próximos 3 meses", "valor": formato_millones(trimestre),
             "detalle": f"{formato_pct(var_trim, signo=True)} contra el año pasado"},
        ],
        "conclusiones": [
            f"En {_texto_periodo(n)} se facturaron {formato_millones(tot_act)}, "
            f"{formato_pct(abs(var))} {'más' if var >= 0 else 'menos'} que en el período anterior.",
            f"{sube[0]} explica la mayor parte de la suba y {baja[0]} es el que más resta.",
            f"Para los próximos 3 meses se esperan {formato_millones(trimestre)} "
            f"({formato_pct(var_trim, signo=True)} contra el mismo trimestre del año pasado).",
            "Diciembre y marzo son los meses más fuertes del año: conviene prepararlos con tiempo.",
        ],
        "secciones": [
            seccion("Cómo evolucionaron los ingresos", grafico=grafico_evolucion, lectura=[
                f"El mejor mes de los últimos 12 fue {etiqueta_mes(*meses[-ver:][mejor_mes])} "
                f"con {formato_millones(total[-ver:][mejor_mes])}.",
                f"Los últimos 12 meses suman {formato_millones(ultimos12)}, "
                f"{formato_pct(variacion_pct(ultimos12, anteriores12), signo=True)} contra los 12 anteriores.",
                "La línea punteada es la facturación del mismo mes del año anterior.",
            ]),
            seccion("Qué clientes explican la variación", grafico=grafico_puente, alto=380,
                    descripcion=f"Diferencia por cliente entre {_texto_periodo(n)} y el período anterior.",
                    lectura=[
                        f"{sube[0]} sumó {formato_pesos(sube[1])} y {baja[0]} restó {formato_pesos(-baja[1])}."
                        if baja[1] < 0 else f"{sube[0]} sumó {formato_pesos(sube[1])}; ningún cliente bajó.",
                        f"{sum(1 for _, d in deltas if d < 0)} de {len(deltas)} clientes facturaron menos que en el período anterior.",
                        "Cada barra azul suma y cada barra roja resta desde el total del período anterior.",
                    ]),
            seccion("Cuánto se espera facturar", grafico=grafico_pronostico, acciones=acciones, lectura=[
                f"Para {etiqueta_mes(*futuros[0])} se esperan {formato_millones(p['valores'][0])}; la banda celeste "
                "es el rango donde debería caer con 80% de probabilidad.",
                "La proyección combina la tendencia de los últimos 24 meses con la estacionalidad de cada mes.",
            ]),
        ],
        "sugerencias": [f"¿Por qué bajó {baja[0]}?", "¿Llegamos a la meta del trimestre?", "¿La suba es estacional o real?"],
        "contexto_ia": {"actual": tot_act, "anterior": tot_ant, "variaciones": dict(deltas),
                        "proyeccion": dict(zip([etiqueta_mes(*f) for f in futuros], p["valores"]))},
    }


# ==========================================================================
# Concentración y riesgo de ingresos
# ==========================================================================
@catalogo.registrar(
    "riesgo", "Concentración y riesgo de ingresos",
    "De qué clientes y sectores dependen los ingresos, cuáles vienen cayendo y qué hacer con cada uno.",
    usa_periodo=False, icono="bi-shield-exclamation",
)
def riesgo(periodo):
    meses, datos = services.facturacion_mensual()
    anual = {c: sum(v[-12:]) for c, v in datos.items()}
    total = sum(anual.values())

    # --- Composición ------------------------------------------------------
    sectores = defaultdict(list)
    for cliente, monto in anual.items():
        sectores[services.CLIENTES[cliente][0]].append((cliente, monto))
    arbol = []
    for i, (sector, items) in enumerate(sorted(sectores.items(), key=lambda s: -sum(m for _, m in s[1]))):
        arbol.append({"name": sector, "itemStyle": {"color": g.SERIES[i % len(g.SERIES)]},
                      "children": [{"name": c, "value": m} for c, m in sorted(items, key=lambda x: -x[1])]})
    grafico_arbol = g.base(
        tooltip={"trigger": "item", "confine": True, "valueFormatter": "fmt:pesos"},
        series=[{
            "type": "treemap", "data": arbol, "roam": False, "nodeClick": False, "breadcrumb": {"show": False},
            "width": "100%", "height": "100%", "top": 0, "left": 0,
            "label": {"show": True, "formatter": "{b}", "color": "#fff", "fontWeight": 600},
            "upperLabel": {"show": True, "height": 24, "color": "#fff", "fontWeight": 700},
            "levels": [{"itemStyle": {"borderColor": "#fff", "borderWidth": 3, "gapWidth": 3}},
                       {"colorAlpha": [0.7, 1], "itemStyle": {"gapWidth": 2, "borderWidth": 0}}],
        }],
    )
    orden = sorted(anual.items(), key=lambda x: -x[1])
    top3 = sum(m for _, m in orden[:3])

    # --- Tendencia por cliente y acciones ---------------------------------
    filas = []
    for cliente, serie in datos.items():
        pendiente, _ = regresion_lineal(serie[-6:])
        filas.append({"cliente": cliente, "ranking": services.CLIENTES[cliente][3],
                      "cambio": variacion_pct(sum(serie[-3:]), sum(serie[-6:-3])),
                      "anual": anual[cliente], "perdida": max(0, -pendiente * 12 * 6)})
    filas.sort(key=lambda f: f["cambio"])
    grafico_tendencia = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        grid={"left": 8, "right": 48, "top": 8, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores("fmt:pct"),
        yAxis=g.eje_categorias([f["cliente"] for f in filas], inverse=True),
        series=[{
            "name": "Cambio últimos 3 meses", "type": "bar", "barMaxWidth": 22,
            "data": [{"value": f["cambio"], "itemStyle": {
                "color": g.NEGATIVO if f["cambio"] < 0 else g.POSITIVO,
                "borderRadius": [0, 4, 4, 0] if f["cambio"] >= 0 else [4, 0, 0, 4]}} for f in filas],
            "label": {"show": True, "position": "right", "formatter": "{c}%", "color": g.TINTA_SUAVE},
        }],
    )
    acciones = []
    for f in filas:
        if f["cambio"] >= -2:
            continue
        if f["ranking"] == "A" or f["anual"] > 1_500_000:
            pr, txt = "alta", "Agendar reunión con el gerente de cuenta esta semana y revisar el nivel de servicio."
        elif f["cambio"] < -6:
            pr, txt = "alta", "Llamar al referente del cliente para entender la caída y ofrecer una propuesta."
        else:
            pr, txt = "media", "Incluir en la ronda de seguimiento comercial del mes."
        acciones.append({"prioridad": pr, "titulo": f"{f['cliente']}: {formato_pct(f['cambio'], signo=True)} en 3 meses",
                         "detalle": f"Factura {formato_millones(f['anual'])} al año. {txt}"})
    crecen = [f for f in filas if f["cambio"] > 2]
    if crecen:
        mejor = max(crecen, key=lambda f: f["cambio"])
        acciones.append({"prioridad": "baja", "titulo": f"{mejor['cliente']}: {formato_pct(mejor['cambio'], signo=True)} en 3 meses",
                         "detalle": "Es el cliente que más crece. Ofrecer servicios adicionales mientras la relación está en alza."})
    en_baja = [f for f in filas if f["cambio"] < -2]
    perdida = round(sum(f["perdida"] for f in en_baja), -3)

    return {
        "kpis": [
            {"label": "Facturación anual", "valor": formato_millones(total), "detalle": "últimos 12 meses"},
            {"label": "Peso de los 3 principales", "valor": f"{round(top3 / total * 100)}%",
             "alerta": top3 / total > .6, "detalle": ", ".join(c for c, _ in orden[:3])},
            {"label": "Clientes en baja", "valor": len(en_baja), "alerta": bool(en_baja),
             "detalle": f"{formato_millones(sum(f['anual'] for f in en_baja))} anuales expuestos"},
            {"label": "Pérdida si sigue la tendencia", "valor": formato_millones(perdida), "alerta": perdida > 0,
             "detalle": "estimada a 12 meses"},
        ],
        "conclusiones": [
            f"Los 3 clientes principales concentran el {round(top3 / total * 100)}% de la facturación anual.",
            f"{arbol[0]['name']} es el sector del que más se depende: "
            f"{round(sum(ch['value'] for ch in arbol[0]['children']) / total * 100)}% de los ingresos.",
            f"{len(en_baja)} clientes vienen bajando; si la tendencia sigue, se pierden unos {formato_millones(perdida)} al año.",
            f"{filas[0]['cliente']} es el caso más urgente ({formato_pct(filas[0]['cambio'], signo=True)} en los últimos 3 meses).",
        ],
        "secciones": [
            seccion("De quién dependen los ingresos", grafico=grafico_arbol, alto=380,
                    descripcion="Facturación de los últimos 12 meses por sector y cliente.", lectura=[
                        f"{orden[0][0]} representa {round(orden[0][1] / total * 100)}% de lo facturado.",
                        "El tamaño de cada bloque es proporcional al monto facturado.",
                    ]),
            seccion("Qué clientes vienen cayendo y qué hacer", grafico=grafico_tendencia, alto=380, acciones=acciones,
                    descripcion="Cambio de los últimos 3 meses contra los 3 anteriores.", lectura=[
                        "En rojo, los clientes que facturan menos; en azul, los que crecen.",
                        "Las acciones están ordenadas por impacto: primero los clientes grandes o de ranking A.",
                    ]),
        ],
        "sugerencias": [f"Armame un guion para la reunión con {filas[0]['cliente']}",
                        "¿Dependemos demasiado de pocos clientes?", "¿Qué clientes podemos crecer?"],
        "contexto_ia": {"anual": anual, "cambios": {f["cliente"]: f["cambio"] for f in filas}},
    }
