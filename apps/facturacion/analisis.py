"""Análisis del módulo Facturación."""
from collections import defaultdict

from apps.core import graficos as g
from apps.core.analisis import Catalogo
from apps.core.estadistica import pronostico, regresion_lineal, variacion_pct
from apps.core.utils import etiqueta_mes, formato_millones, formato_pct, formato_pesos, siguientes_meses

from . import services

catalogo = Catalogo()

MESES_PERIODO = {"30": 1, "90": 3, "365": 12}


def _texto_periodo(n):
    return "el último mes" if n == 1 else f"los últimos {n} meses"


# --------------------------------------------------------------------------
# Descriptivo
# --------------------------------------------------------------------------
@catalogo.registrar(
    "descriptivo", "composicion", "Composición de la facturación",
    "Cuánto factura cada cliente y cada sector en el período.",
)
def composicion(periodo):
    n = MESES_PERIODO[periodo]
    meses, datos = services.facturacion_mensual()
    por_cliente = {c: sum(v[-n:]) for c, v in datos.items()}
    total = sum(por_cliente.values())

    sectores = defaultdict(list)
    for cliente, monto in por_cliente.items():
        sectores[services.CLIENTES[cliente][0]].append((cliente, monto))

    arbol = []
    for i, (sector, items) in enumerate(sorted(sectores.items(), key=lambda s: -sum(m for _, m in s[1]))):
        arbol.append({
            "name": sector,
            "itemStyle": {"color": g.SERIES[i % len(g.SERIES)]},
            "children": [{"name": c, "value": m} for c, m in sorted(items, key=lambda x: -x[1])],
        })

    opcion = g.base(
        tooltip={"trigger": "item", "confine": True, "valueFormatter": "fmt:pesos"},
        series=[{
            "type": "treemap", "data": arbol, "roam": False, "nodeClick": False,
            "breadcrumb": {"show": False}, "width": "100%", "height": "100%", "top": 0, "left": 0,
            "label": {"show": True, "formatter": "{b}", "color": "#fff", "fontWeight": 600},
            "upperLabel": {"show": True, "height": 24, "color": "#fff", "fontWeight": 700},
            "levels": [
                {"itemStyle": {"borderColor": "#fff", "borderWidth": 3, "gapWidth": 3}},
                {"colorAlpha": [0.7, 1], "itemStyle": {"gapWidth": 2, "borderWidth": 0}},
            ],
        }],
    )

    top = max(por_cliente, key=por_cliente.get)
    top3 = sum(sorted(por_cliente.values(), reverse=True)[:3])
    sector_top = arbol[0]["name"]
    monto_sector = sum(ch["value"] for ch in arbol[0]["children"])

    return {
        "kpis": [
            {"label": "Facturado", "valor": formato_millones(total), "detalle": _texto_periodo(n)},
            {"label": "Cliente principal", "valor": top,
             "detalle": f"{round(por_cliente[top] / total * 100)}% del total"},
            {"label": "Sector principal", "valor": sector_top,
             "detalle": f"{round(monto_sector / total * 100)}% del total"},
            {"label": "Clientes facturados", "valor": len(por_cliente),
             "detalle": f"ticket medio {formato_millones(total / len(por_cliente))}"},
        ],
        "grafico": opcion,
        "grafico_alto": 380,
        "lectura": [
            f"Los 3 clientes más grandes concentran el {round(top3 / total * 100)}% de lo facturado.",
            f"{sector_top} es el sector más importante con {formato_millones(monto_sector)}.",
            "El tamaño de cada bloque es proporcional al monto facturado.",
        ],
        "tabla": {
            "titulo": "Facturación por cliente",
            "columnas": ["Cliente", "Sector", "Monto", "% del total"],
            "filas": [[c, services.CLIENTES[c][0], formato_pesos(m), formato_pct(m / total * 100)]
                      for c, m in sorted(por_cliente.items(), key=lambda x: -x[1])],
        },
        "sugerencias": ["¿Dependemos demasiado de pocos clientes?", "¿Qué sector conviene desarrollar?"],
        "contexto_ia": {"total": total, "por_cliente": por_cliente},
    }


# --------------------------------------------------------------------------
# Diagnóstico
# --------------------------------------------------------------------------
@catalogo.registrar(
    "diagnostico", "variacion", "Qué explica la variación",
    "Qué clientes hicieron subir o bajar la facturación contra el período anterior.",
)
def variacion(periodo):
    n = MESES_PERIODO[periodo]
    meses, datos = services.facturacion_mensual()
    actual = {c: sum(v[-n:]) for c, v in datos.items()}
    anterior = {c: sum(v[-2 * n:-n]) for c, v in datos.items()}
    deltas = sorted(((c, actual[c] - anterior[c]) for c in datos), key=lambda x: -x[1])

    tot_ant, tot_act = sum(anterior.values()), sum(actual.values())
    etiquetas = ["Período anterior"] + [c for c, _ in deltas] + ["Período actual"]
    base_inv, subida, bajada = [0], [None], [None]
    acumulado = tot_ant
    for _, d in deltas:
        if d >= 0:
            base_inv.append(acumulado); subida.append(d); bajada.append(None)
        else:
            base_inv.append(acumulado + d); subida.append(None); bajada.append(-d)
        acumulado += d
    base_inv.append(0)
    totales = [tot_ant] + [None] * len(deltas) + [tot_act]

    opcion = g.base(
        legend=g.leyenda(data=["Total", "Sube", "Baja"]),
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pesos"},
        grid={"left": 8, "right": 16, "top": 36, "bottom": 8, "containLabel": True},
        xAxis=g.eje_categorias(etiquetas, axisLabel={"interval": 0, "rotate": 35, "color": g.TINTA_SUAVE}),
        yAxis=g.eje_valores("fmt:pesos_k", min=round(min(tot_ant, tot_act) * .85, -5)),
        series=[
            {"name": "_base", "type": "bar", "stack": "w", "data": base_inv, "silent": True,
             "itemStyle": {"color": "transparent"}, "tooltip": {"show": False}},
            g.barras("Total", totales, g.NEUTRO, stack="w"),
            g.barras("Sube", subida, g.POSITIVO, stack="w"),
            g.barras("Baja", bajada, g.NEGATIVO, stack="w"),
        ],
    )

    var = variacion_pct(tot_act, tot_ant)
    sube, baja = deltas[0], deltas[-1]
    return {
        "kpis": [
            {"label": "Variación", "valor": formato_millones(abs(tot_act - tot_ant)),
             "detalle": f"{'sube' if var >= 0 else 'baja'} {formato_pct(abs(var))} contra el período anterior",
             "alerta": var < 0},
            {"label": "Mayor aporte", "valor": sube[0], "detalle": f"+{formato_pesos(sube[1])}"},
            {"label": "Mayor caída", "valor": baja[0], "detalle": f"−{formato_pesos(-baja[1])}",
             "alerta": baja[1] < 0},
            {"label": "Clientes en baja", "valor": sum(1 for _, d in deltas if d < 0),
             "detalle": f"de {len(deltas)} clientes"},
        ],
        "grafico": opcion,
        "grafico_alto": 380,
        "lectura": [
            f"La facturación {'subió' if var >= 0 else 'bajó'} {formato_pct(abs(var))} comparando {_texto_periodo(n)} "
            f"con los {n if n > 1 else ''} {'meses' if n > 1 else 'mes'} anteriores.",
            f"{sube[0]} explica la mayor parte de la suba; {baja[0]} es el que más resta.",
            "Cada barra azul suma y cada barra roja resta desde el total del período anterior.",
        ],
        "sugerencias": [f"¿Por qué bajó {baja[0]}?", "¿La suba es estacional o real?"],
        "contexto_ia": {"anterior": tot_ant, "actual": tot_act, "variaciones": dict(deltas)},
    }


# --------------------------------------------------------------------------
# Predictivo
# --------------------------------------------------------------------------
def _kpi_tendencia(pendiente, promedio_mensual):
    """La tendencia como % del promedio mensual: con menos de 0,2% se considera estable."""
    pct = pendiente / promedio_mensual * 100 if promedio_mensual else 0
    if abs(pct) < 0.2:
        return {"label": "Tendencia", "valor": "Estable", "detalle": "sin crecimiento ni caída de fondo"}
    return {"label": "Tendencia", "valor": formato_pct(pct, signo=True), "alerta": pct < 0,
            "detalle": f"{'sube' if pct > 0 else 'baja'} {formato_pesos(abs(pendiente))} por mes"}


@catalogo.registrar(
    "predictivo", "proyeccion", "Proyección de facturación",
    "Cuánto se espera facturar en los próximos 3 meses.",
    usa_periodo=False,
)
def proyeccion(periodo):
    meses, total = services.total_mensual()
    p = pronostico(total, pasos=3)
    futuros = siguientes_meses(meses[-1], 3)
    ver = 12
    opcion = g.serie_pronostico(
        [round(v) for v in total[-ver:]], p,
        [etiqueta_mes(*m) for m in meses[-ver:]], [etiqueta_mes(*m) for m in futuros],
        nombre="Facturado", formato="fmt:pesos",
    )
    opcion["yAxis"]["axisLabel"]["formatter"] = "fmt:pesos_k"
    opcion["yAxis"]["min"] = round(min(total[-ver:]) * .8, -5)

    trimestre = sum(p["valores"])
    trimestre_ant = sum(total[-12:-9])
    return {
        "kpis": [
            {"label": f"Esperado en {etiqueta_mes(*futuros[0])}", "valor": formato_millones(p["valores"][0]),
             "detalle": f"entre {formato_millones(p['inferior'][0])} y {formato_millones(p['superior'][0])}"},
            {"label": "Próximos 3 meses", "valor": formato_millones(trimestre),
             "detalle": f"{formato_pct(variacion_pct(trimestre, trimestre_ant), signo=True)} contra el mismo trimestre del año pasado"},
            _kpi_tendencia(p["pendiente"], sum(total[-12:]) / 12),
            {"label": "Pico esperado", "valor": etiqueta_mes(*futuros[p["valores"].index(max(p["valores"]))]),
             "detalle": formato_millones(max(p["valores"]))},
        ],
        "grafico": opcion,
        "lectura": [
            f"Para {etiqueta_mes(*futuros[0])} se esperan {formato_millones(p['valores'][0])}; "
            "la banda celeste es el rango donde debería caer con 80% de probabilidad.",
            "La proyección combina la tendencia de los últimos 24 meses con la estacionalidad: diciembre "
            "y marzo suelen ser los meses más altos.",
            "Si un mes real cae fuera de la banda, conviene revisarlo en «Qué explica la variación».",
        ],
        "tabla": {
            "titulo": "Proyección mes a mes",
            "columnas": ["Mes", "Esperado", "Mínimo", "Máximo"],
            "filas": [[etiqueta_mes(*f), formato_pesos(v), formato_pesos(lo), formato_pesos(hi)]
                      for f, v, lo, hi in zip(futuros, p["valores"], p["inferior"], p["superior"])],
        },
        "sugerencias": ["¿Llegamos a la meta del trimestre?", "¿Qué pasa si perdemos a Disco?"],
        "contexto_ia": {"proyeccion": dict(zip([etiqueta_mes(*f) for f in futuros], p["valores"]))},
    }


# --------------------------------------------------------------------------
# Prescriptivo
# --------------------------------------------------------------------------
@catalogo.registrar(
    "prescriptivo", "retencion", "Clientes a cuidar",
    "Qué clientes vienen bajando su facturación y qué hacer con cada uno.",
    usa_periodo=False,
)
def retencion(periodo):
    meses, datos = services.facturacion_mensual()
    filas = []
    for cliente, serie in datos.items():
        ult, prev = sum(serie[-3:]), sum(serie[-6:-3])
        pendiente, _ = regresion_lineal(serie[-6:])
        filas.append({
            "cliente": cliente, "ranking": services.CLIENTES[cliente][3],
            "cambio": variacion_pct(ult, prev), "anual": sum(serie[-12:]),
            "perdida_anual": max(0, -pendiente * 12 * 6),
        })
    filas.sort(key=lambda f: f["cambio"])

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
        acciones.append({
            "prioridad": pr,
            "titulo": f"{f['cliente']}: {formato_pct(f['cambio'], signo=True)} en los últimos 3 meses",
            "detalle": f"Factura {formato_millones(f['anual'])} al año. {txt}",
        })

    colores = [g.NEGATIVO if f["cambio"] < 0 else g.POSITIVO for f in filas]
    opcion = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        grid={"left": 8, "right": 40, "top": 8, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores("fmt:pct"),
        yAxis=g.eje_categorias([f["cliente"] for f in filas], inverse=True),
        series=[{
            "name": "Cambio últimos 3 meses", "type": "bar", "barMaxWidth": 22,
            "data": [{"value": f["cambio"], "itemStyle": {"color": c,
                      "borderRadius": [0, 4, 4, 0] if f["cambio"] >= 0 else [4, 0, 0, 4]}}
                     for f, c in zip(filas, colores)],
            "label": {"show": True, "position": "right", "formatter": "{c}%", "color": g.TINTA_SUAVE},
        }],
    )

    en_baja = [f for f in filas if f["cambio"] < -2]
    return {
        "kpis": [
            {"label": "Clientes en baja", "valor": len(en_baja), "alerta": bool(en_baja),
             "detalle": "más de 2% de caída"},
            {"label": "Facturación expuesta", "valor": formato_millones(sum(f["anual"] for f in en_baja)),
             "detalle": "anual de esos clientes"},
            {"label": "Pérdida si sigue la tendencia", "valor": formato_millones(sum(f["perdida_anual"] for f in en_baja)),
             "detalle": "estimada a 12 meses", "alerta": True},
            {"label": "Clientes creciendo", "valor": sum(1 for f in filas if f["cambio"] > 2),
             "detalle": "más de 2% de suba"},
        ],
        "grafico": opcion,
        "grafico_alto": 380,
        "lectura": [
            f"{filas[0]['cliente']} es el cliente con mayor caída ({formato_pct(filas[0]['cambio'], signo=True)}) comparando "
            "los últimos 3 meses con los 3 anteriores.",
            "Las acciones están ordenadas por impacto: primero los clientes grandes o de ranking A.",
            "Los clientes en azul están creciendo: son candidatos para ampliar servicios.",
        ],
        "acciones": acciones,
        "sugerencias": [f"Armame un guion para la reunión con {filas[0]['cliente']}", "¿Qué clientes podemos crecer?"],
        "contexto_ia": {"cambios": {f["cliente"]: f["cambio"] for f in filas}},
    }
