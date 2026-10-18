"""Análisis del módulo Clientes."""
from collections import defaultdict

from apps.core import graficos as g
from apps.core.analisis import Catalogo
from apps.core.utils import formato_millones, formato_pct, formato_pesos

from . import services

catalogo = Catalogo()


# --------------------------------------------------------------------------
# Descriptivo
# --------------------------------------------------------------------------
@catalogo.registrar(
    "descriptivo", "cartera", "Mapa de la cartera",
    "Clientes activos por sector y ranking, con el peso de cada uno en la facturación.",
    usa_periodo=False,
)
def cartera(periodo):
    act = services.activos()
    total = sum(c["facturacion"] for c in act)

    sectores = defaultdict(list)
    for c in act:
        sectores[c["sector"]].append(c)
    orden = sorted(sectores, key=lambda s: -sum(c["facturacion"] for c in sectores[s]))

    datos = []
    for i, s in enumerate(orden):
        datos.append({
            "name": s, "itemStyle": {"color": g.SERIES[i % len(g.SERIES)]},
            "children": [{"name": c["nombre"], "value": c["facturacion"]}
                         for c in sorted(sectores[s], key=lambda c: -c["facturacion"])],
        })

    opcion = g.base(
        tooltip={"trigger": "item", "confine": True, "valueFormatter": "fmt:pesos"},
        series=[{
            "type": "sunburst", "data": datos, "radius": ["18%", "92%"], "sort": None,
            "nodeClick": False,
            "itemStyle": {"borderColor": "#fff", "borderWidth": 2, "borderRadius": 4},
            "levels": [{}, {"label": {"rotate": "tangential", "fontWeight": 600, "color": "#fff", "minAngle": 25}},
                       {"label": {"align": "right", "color": g.TINTA, "fontSize": 11, "minAngle": 7},
                        "itemStyle": {"opacity": 0.75}}],
        }],
    )

    por_ranking = defaultdict(int)
    for c in act:
        por_ranking[c["ranking"]] += 1
    nuevos = [c for c in act if (c["fecha_alta"] and (services.hace(0) - c["fecha_alta"]).days <= 365)]

    return {
        "kpis": [
            {"label": "Clientes activos", "valor": len(act), "detalle": f"en {len(sectores)} sectores"},
            {"label": "Ranking A", "valor": por_ranking["A"],
             "detalle": f"{round(sum(c['facturacion'] for c in act if c['ranking'] == 'A') / total * 100)}% de la facturación"},
            {"label": "Facturación anual", "valor": formato_millones(total), "detalle": "de la cartera activa"},
            {"label": "Nuevos en el año", "valor": len(nuevos),
             "detalle": ", ".join(c["nombre"] for c in nuevos) or "ninguno"},
        ],
        "grafico": opcion,
        "grafico_alto": 420,
        "lectura": [
            f"{orden[0]} es el sector con más peso: {len(sectores[orden[0]])} clientes y "
            f"{round(sum(c['facturacion'] for c in sectores[orden[0]]) / total * 100)}% de la facturación.",
            f"El anillo interior son los sectores; el exterior, los clientes de cada uno según lo que facturan.",
        ],
        "tabla": {
            "titulo": "Cartera activa",
            "columnas": ["Cliente", "Sector", "Ranking", "Tendencia", "Facturación anual"],
            "filas": [[c["nombre"], c["sector"], c["ranking"], c["tendencia"], formato_pesos(c["facturacion"])]
                      for c in sorted(act, key=lambda c: -c["facturacion"])],
        },
        "sugerencias": ["¿Qué sector tiene más potencial?", "¿Cuántos clientes C podrían pasar a B?"],
        "contexto_ia": {"sectores": {s: len(v) for s, v in sectores.items()}, "ranking": dict(por_ranking)},
    }


# --------------------------------------------------------------------------
# Diagnóstico
# --------------------------------------------------------------------------
@catalogo.registrar(
    "diagnostico", "concentracion", "Concentración de la cartera",
    "Análisis de Pareto: cuántos clientes explican el 80% de la facturación anual.",
    usa_periodo=False,
)
def concentracion(periodo):
    act = sorted(services.activos(), key=lambda c: -c["facturacion"])
    total = sum(c["facturacion"] for c in act)
    part = [round(c["facturacion"] / total * 100, 1) for c in act]
    acum, s = [], 0
    for p in part:
        s += p
        acum.append(round(s, 1))
    corte = next(i for i, a in enumerate(acum) if a >= 80) + 1
    hhi = round(sum(p * p for p in part))

    opcion = g.base(
        legend=g.leyenda(),
        tooltip={"trigger": "axis", "confine": True, "valueFormatter": "fmt:pct"},
        grid={"left": 8, "right": 16, "top": 36, "bottom": 8, "containLabel": True},
        xAxis=g.eje_categorias([c["nombre"] for c in act], axisLabel={"interval": 0, "rotate": 35, "color": g.TINTA_SUAVE}),
        yAxis=g.eje_valores("fmt:pct", max=100),
        series=[
            g.barras("Participación", [{"value": p, "itemStyle": {"color": g.SERIES[0] if i < corte else g.AZUL[1]}}
                                       for i, p in enumerate(part)]),
            g.linea("Acumulado", acum, g.SERIES[1],
                    markLine={"silent": True, "symbol": "none", "lineStyle": {"color": g.TINTA_SUAVE, "type": "dashed"},
                              "label": {"formatter": "80%", "color": g.TINTA_SUAVE}, "data": [{"yAxis": 80}]}),
        ],
    )

    nivel = "alta" if hhi > 2500 else "moderada" if hhi > 1500 else "baja"
    return {
        "kpis": [
            {"label": "Clientes que hacen el 80%", "valor": corte, "detalle": f"de {len(act)} activos"},
            {"label": "Peso del principal", "valor": formato_pct(part[0]), "detalle": act[0]["nombre"], "alerta": part[0] > 25},
            {"label": "Top 3", "valor": formato_pct(acum[2]), "detalle": "de la facturación"},
            {"label": "Índice de concentración", "valor": formato_pesos(hhi).replace("$ ", ""),
             "detalle": f"concentración {nivel} (HHI)", "alerta": nivel == "alta"},
        ],
        "grafico": opcion,
        "lectura": [
            f"{corte} clientes explican el 80% de la facturación; el resto aporta {round(100 - acum[corte - 1])}%.",
            f"Perder a {act[0]['nombre']} implicaría resignar {formato_pct(part[0])} de los ingresos.",
            "Un HHI mayor a 2.500 indica alta dependencia de pocos clientes; entre 1.500 y 2.500, moderada.",
        ],
        "sugerencias": ["¿Cuánto riesgo tenemos con Antel?", "¿Cómo diversificar la cartera?"],
        "contexto_ia": {"participacion": dict(zip([c["nombre"] for c in act], part)), "hhi": hhi},
    }


# --------------------------------------------------------------------------
# Predictivo
# --------------------------------------------------------------------------
def riesgo_abandono(c):
    """Probabilidad estimada (0-100) de que el cliente deje de pedir en los próximos 6 meses.

    Combina días sin pedir, caída de pedidos contra el año anterior y la tendencia.
    """
    inactividad = min(c["dias_sin_pedir"] / 180, 1)
    caida = 0
    if c["pedidos_prev"]:
        caida = max(0, min(1, (c["pedidos_prev"] - c["pedidos_12m"]) / c["pedidos_prev"]))
    tendencia = {"Bajando": 1, "Estable": .3, "Creciendo": 0}[c["tendencia"]]
    return round((inactividad * .45 + caida * .35 + tendencia * .20) * 100)


@catalogo.registrar(
    "predictivo", "abandono", "Riesgo de abandono",
    "Probabilidad de que cada cliente deje de pedir en los próximos 6 meses.",
    usa_periodo=False,
)
def abandono(periodo):
    act = sorted(services.activos(), key=riesgo_abandono, reverse=True)
    def color(r):
        return g.ESTADO["critico"] if r >= 60 else g.ESTADO["serio"] if r >= 35 else g.ESTADO["bien"]

    opcion = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        grid={"left": 8, "right": 40, "top": 8, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores("fmt:pct", max=100),
        yAxis=g.eje_categorias([c["nombre"] for c in act], inverse=True),
        series=[{
            "name": "Riesgo de abandono", "type": "bar", "barMaxWidth": 20,
            "data": [{"value": riesgo_abandono(c), "itemStyle": {"color": color(riesgo_abandono(c)),
                      "borderRadius": [0, 4, 4, 0]}} for c in act],
            "label": {"show": True, "position": "right", "formatter": "{c}%", "color": g.TINTA_SUAVE},
            "markLine": {"silent": True, "symbol": "none", "lineStyle": {"color": g.EJE, "type": "dashed"},
                         "label": {"formatter": "Alto", "color": g.TINTA_SUAVE}, "data": [{"xAxis": 60}]},
        }],
    )

    altos = [c for c in act if riesgo_abandono(c) >= 60]
    medios = [c for c in act if 35 <= riesgo_abandono(c) < 60]
    expuesta = sum(c["facturacion"] * riesgo_abandono(c) / 100 for c in act)
    return {
        "kpis": [
            {"label": "Riesgo alto", "valor": len(altos), "alerta": bool(altos), "detalle": "60% o más"},
            {"label": "Riesgo medio", "valor": len(medios), "detalle": "entre 35% y 60%"},
            {"label": "Facturación en riesgo", "valor": formato_millones(sum(c["facturacion"] for c in altos)),
             "detalle": "anual de clientes en riesgo alto"},
            {"label": "Pérdida esperada", "valor": formato_millones(expuesta),
             "detalle": "facturación × probabilidad de abandono"},
        ],
        "grafico": opcion,
        "grafico_alto": 420,
        "lectura": [
            f"{act[0]['nombre']} tiene la mayor probabilidad de abandono ({riesgo_abandono(act[0])}%): "
            f"lleva {act[0]['dias_sin_pedir']} días sin pedir.",
            "El modelo pondera días sin pedir (45%), caída de pedidos contra el año anterior (35%) y tendencia (20%).",
            "Rojo: riesgo alto. Naranja: medio. Verde: bajo.",
        ],
        "tabla": {
            "titulo": "Detalle del riesgo",
            "columnas": ["Cliente", "Riesgo", "Días sin pedir", "Pedidos 12m", "Año anterior", "Tendencia"],
            "filas": [[c["nombre"], f"{riesgo_abandono(c)}%", c["dias_sin_pedir"], c["pedidos_12m"],
                       c["pedidos_prev"], c["tendencia"]] for c in act[:8]],
        },
        "sugerencias": ["¿Por qué UTE tiene riesgo alto?", "¿Qué señales anticipan un abandono?"],
        "contexto_ia": {"riesgos": {c["nombre"]: riesgo_abandono(c) for c in act}},
    }


# --------------------------------------------------------------------------
# Prescriptivo
# --------------------------------------------------------------------------
CUADRANTES = {
    "retener": ("Retener ya", "alta",
                "Cliente valioso con alto riesgo. Visita del gerente comercial en los próximos 7 días y propuesta de mejora de servicio."),
    "reactivar": ("Reactivar", "media",
                  "Riesgo alto pero menor facturación. Incluir en campaña de reactivación con oferta para el próximo pedido."),
    "cuidar": ("Cuidar", "baja",
               "Cliente valioso y estable. Mantener contacto mensual y explorar nuevos puestos o sedes."),
    "desarrollar": ("Desarrollar", "baja",
                    "Bajo riesgo y facturación chica. Oportunidad de crecimiento con servicios adicionales."),
}


@catalogo.registrar(
    "prescriptivo", "plan", "Plan de acción comercial",
    "Qué hacer con cada cliente según su valor y su riesgo de abandono.",
    usa_periodo=False,
)
def plan(periodo):
    act = services.activos()
    corte_valor = sorted(c["facturacion"] for c in act)[len(act) // 2]

    def cuadrante(c):
        alto_valor = c["facturacion"] >= corte_valor
        alto_riesgo = riesgo_abandono(c) >= 40
        return ("retener" if alto_valor else "reactivar") if alto_riesgo else ("cuidar" if alto_valor else "desarrollar")

    colores = {"retener": g.ESTADO["critico"], "reactivar": g.ESTADO["serio"],
               "cuidar": g.SERIES[0], "desarrollar": g.SERIES[2]}
    series = []
    for k, (nombre, _, _) in CUADRANTES.items():
        series.append({
            "name": nombre, "type": "scatter", "symbolSize": 16,
            "itemStyle": {"color": colores[k], "borderColor": "#fff", "borderWidth": 2},
            "data": [[round(c["facturacion"] / 1000), riesgo_abandono(c), c["nombre"]] for c in act if cuadrante(c) == k],
            "label": {"show": True, "formatter": "{@[2]}", "position": "right", "fontSize": 11, "color": g.TINTA_SUAVE},
            "labelLayout": {"moveOverlap": "shiftY"},
        })
    series[0]["markLine"] = {
        "silent": True, "symbol": "none", "lineStyle": {"color": g.EJE, "type": "dashed"}, "label": {"show": False},
        "data": [{"yAxis": 40}, {"xAxis": round(corte_valor / 1000)}],
    }

    opcion = g.base(
        legend=g.leyenda(),
        tooltip={"trigger": "item", "confine": True,
                 "formatter": "{@[2]}<br>Facturación: $ {@[0]}k<br>Riesgo: {@[1]}%"},
        grid={"left": 36, "right": 90, "top": 40, "bottom": 40, "containLabel": True},
        xAxis=g.eje_valores("fmt:num", name="Facturación anual ($ miles, escala logarítmica)", nameLocation="middle",
                            nameGap=30, type="log", splitLine={"show": False}),
        yAxis=g.eje_valores("fmt:pct", name="Riesgo de abandono", nameLocation="middle", nameGap=44, max=100),
        series=series,
    )

    orden = {"retener": 0, "reactivar": 1, "cuidar": 2, "desarrollar": 3}
    acciones = []
    for c in sorted(act, key=lambda c: (orden[cuadrante(c)], -c["facturacion"])):
        nombre, pr, txt = CUADRANTES[cuadrante(c)]
        acciones.append({"prioridad": pr, "titulo": f"{c['nombre']} · {nombre}",
                         "detalle": f"Factura {formato_millones(c['facturacion'])} al año, riesgo {riesgo_abandono(c)}%. {txt}"})

    retener = [c for c in act if cuadrante(c) == "retener"]
    return {
        "kpis": [
            {"label": "Retener ya", "valor": len(retener), "alerta": bool(retener),
             "detalle": formato_millones(sum(c["facturacion"] for c in retener)) + " anuales en juego"},
            {"label": "Reactivar", "valor": sum(1 for c in act if cuadrante(c) == "reactivar"), "detalle": "campaña comercial"},
            {"label": "Cuidar", "valor": sum(1 for c in act if cuadrante(c) == "cuidar"), "detalle": "clientes estables y valiosos"},
            {"label": "Desarrollar", "valor": sum(1 for c in act if cuadrante(c) == "desarrollar"), "detalle": "potencial de crecimiento"},
        ],
        "grafico": opcion,
        "grafico_alto": 420,
        "lectura": [
            "Arriba a la derecha están los clientes que más importa retener: facturan mucho y tienen riesgo alto.",
            "Las líneas punteadas marcan la facturación mediana y el umbral de 40% de riesgo.",
            "El eje de facturación es logarítmico para que se vean bien tanto los clientes grandes como los chicos.",
        ],
        "acciones": acciones[:7],
        "sugerencias": ["Armame la agenda de visitas de esta semana", "¿Qué le ofrezco a un cliente para reactivarlo?"],
        "contexto_ia": {"cuadrantes": {c["nombre"]: CUADRANTES[cuadrante(c)][0] for c in act}},
    }
