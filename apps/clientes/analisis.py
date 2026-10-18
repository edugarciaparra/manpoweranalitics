"""Análisis del módulo Clientes."""
from collections import defaultdict

from apps.core import graficos as g
from apps.core.analisis import Catalogo, seccion
from apps.core.utils import formato_millones, formato_pct, formato_pesos

from . import services

catalogo = Catalogo()


def riesgo_abandono(c):
    """Probabilidad estimada (0-100) de que el cliente deje de pedir en los próximos 6 meses.

    Combina días sin pedir (45%), caída de pedidos contra el año anterior (35%) y tendencia (20%).
    """
    inactividad = min(c["dias_sin_pedir"] / 180, 1)
    caida = 0
    if c["pedidos_prev"]:
        caida = max(0, min(1, (c["pedidos_prev"] - c["pedidos_12m"]) / c["pedidos_prev"]))
    tendencia = {"Bajando": 1, "Estable": .3, "Creciendo": 0}[c["tendencia"]]
    return round((inactividad * .45 + caida * .35 + tendencia * .20) * 100)


# ==========================================================================
# Salud de la cartera
# ==========================================================================
@catalogo.registrar(
    "cartera", "Salud de la cartera",
    "Cómo está compuesta la cartera, cuánto depende de pocos clientes y cómo diversificarla.",
    usa_periodo=False, icono="bi-heart-pulse",
)
def cartera(periodo):
    act = sorted(services.activos(), key=lambda c: -c["facturacion"])
    total = sum(c["facturacion"] for c in act)

    # --- Composición ------------------------------------------------------
    sectores = defaultdict(list)
    for c in act:
        sectores[c["sector"]].append(c)
    orden_s = sorted(sectores, key=lambda s: -sum(c["facturacion"] for c in sectores[s]))
    datos = [{"name": s, "itemStyle": {"color": g.SERIES[i % len(g.SERIES)]},
              "children": [{"name": c["nombre"], "value": c["facturacion"]} for c in sectores[s]]}
             for i, s in enumerate(orden_s)]
    grafico_mapa = g.base(
        tooltip={"trigger": "item", "confine": True, "valueFormatter": "fmt:pesos"},
        series=[{
            "type": "sunburst", "data": datos, "radius": ["18%", "92%"], "sort": None, "nodeClick": False,
            "itemStyle": {"borderColor": "#fff", "borderWidth": 2, "borderRadius": 4},
            "levels": [{}, {"label": {"rotate": "tangential", "fontWeight": 600, "color": "#fff", "minAngle": 25}},
                       {"label": {"align": "right", "color": g.TINTA, "fontSize": 11, "minAngle": 7},
                        "itemStyle": {"opacity": 0.75}}],
        }],
    )
    peso_sector = sum(c["facturacion"] for c in sectores[orden_s[0]]) / total * 100

    # --- Concentración (Pareto) --------------------------------------------
    part = [round(c["facturacion"] / total * 100, 1) for c in act]
    acum, s = [], 0
    for p in part:
        s += p
        acum.append(round(s, 1))
    corte = next(i for i, a in enumerate(acum) if a >= 80) + 1
    hhi = round(sum(p * p for p in part))
    nivel = "alta" if hhi > 2500 else "moderada" if hhi > 1500 else "baja"
    grafico_pareto = g.base(
        legend=g.leyenda(),
        tooltip={"trigger": "axis", "confine": True, "valueFormatter": "fmt:pct"},
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

    # --- Qué hacer --------------------------------------------------------
    chicos_creciendo = [c for c in act[corte:] if c["tendencia"] == "Creciendo"]
    acciones = [{
        "prioridad": "alta" if part[0] > 25 else "media",
        "titulo": f"Bajar la dependencia de {act[0]['nombre']}",
        "detalle": f"Representa {formato_pct(part[0])} de la facturación. Fijar una meta de que ningún cliente "
                   "supere el 25% creciendo en los clientes medianos.",
    }]
    for c in chicos_creciendo[:3]:
        acciones.append({"prioridad": "media", "titulo": f"Desarrollar a {c['nombre']}",
                         "detalle": f"Está creciendo y hoy factura {formato_millones(c['facturacion'])}. "
                                    "Proponer nuevos puestos o sedes para ampliar la cuenta."})
    sectores_chicos = [s for s in orden_s if len(sectores[s]) == 1]
    if sectores_chicos:
        acciones.append({"prioridad": "baja", "titulo": f"Sumar clientes en {', '.join(sectores_chicos[:2])}",
                         "detalle": "Son sectores con un solo cliente: una baja ahí deja al sector sin presencia."})

    return {
        "kpis": [
            {"label": "Clientes activos", "valor": len(act), "detalle": f"en {len(sectores)} sectores"},
            {"label": "Clientes que hacen el 80%", "valor": corte, "detalle": f"de {len(act)} activos"},
            {"label": "Peso del principal", "valor": formato_pct(part[0]), "alerta": part[0] > 25,
             "detalle": act[0]["nombre"]},
            {"label": "Índice de concentración", "valor": formato_pesos(hhi).replace("$ ", ""),
             "alerta": nivel == "alta", "detalle": f"concentración {nivel} (HHI)"},
        ],
        "conclusiones": [
            f"{corte} de {len(act)} clientes explican el 80% de la facturación.",
            f"{act[0]['nombre']} pesa {formato_pct(part[0])}: perderlo tendría un impacto muy fuerte.",
            f"{orden_s[0]} es el sector principal con {round(peso_sector)}% de los ingresos.",
            f"Hay {len(chicos_creciendo)} clientes chicos creciendo: son la mejor vía para diversificar."
            if chicos_creciendo else "No hay clientes chicos creciendo: diversificar requiere sumar clientes nuevos.",
        ],
        "secciones": [
            seccion("Cómo está compuesta la cartera", grafico=grafico_mapa, alto=420,
                    descripcion="Clientes activos por sector, según lo que facturan en el año.", lectura=[
                        f"{orden_s[0]}: {len(sectores[orden_s[0]])} clientes y {round(peso_sector)}% de la facturación.",
                        "El anillo interior son los sectores; el exterior, los clientes de cada uno.",
                    ]),
            seccion("Cuánto depende de pocos clientes", grafico=grafico_pareto, acciones=acciones, lectura=[
                f"{corte} clientes explican el 80%; el resto aporta {round(100 - acum[corte - 1])}%.",
                f"El índice HHI es {formato_pesos(hhi).replace(chr(36) + chr(160), '')}: concentración {nivel}. "
                "Más de 2.500 es alta; entre 1.500 y 2.500, moderada.",
            ]),
        ],
        "sugerencias": ["¿Cuánto riesgo tenemos con Antel?", "¿Cómo diversificar la cartera?",
                        "¿Qué sector conviene desarrollar?"],
        "contexto_ia": {"participacion": dict(zip([c["nombre"] for c in act], part)), "hhi": hhi},
    }


# ==========================================================================
# Riesgo de abandono y plan comercial
# ==========================================================================
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
    "abandono", "Riesgo de abandono y plan comercial",
    "Qué clientes pueden dejar de pedir, por qué, cuánto se arriesga y qué hacer con cada uno.",
    usa_periodo=False, icono="bi-person-x",
)
def abandono(periodo):
    act = sorted(services.activos(), key=riesgo_abandono, reverse=True)

    # --- Riesgo por cliente -----------------------------------------------
    def color(r):
        return g.ESTADO["critico"] if r >= 60 else g.ESTADO["serio"] if r >= 35 else g.ESTADO["bien"]
    grafico_riesgo = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        grid={"left": 8, "right": 48, "top": 8, "bottom": 8, "containLabel": True},
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
    esperada = sum(c["facturacion"] * riesgo_abandono(c) / 100 for c in act)

    # --- Por qué: señales de cada cliente en riesgo -----------------------
    filas_senales = []
    for c in act[:6]:
        caida = (f"{formato_pct((c['pedidos_12m'] - c['pedidos_prev']) / c['pedidos_prev'] * 100, signo=True, decimales=0)}"
                 if c["pedidos_prev"] else "nuevo")
        filas_senales.append([c["nombre"], f"{riesgo_abandono(c)}%", c["dias_sin_pedir"], caida, c["tendencia"]])

    # --- Plan: valor contra riesgo ----------------------------------------
    corte_valor = sorted(c["facturacion"] for c in act)[len(act) // 2]

    def cuadrante(c):
        alto_valor = c["facturacion"] >= corte_valor
        return ("retener" if alto_valor else "reactivar") if riesgo_abandono(c) >= 40 else \
               ("cuidar" if alto_valor else "desarrollar")

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
    series[0]["markLine"] = {"silent": True, "symbol": "none", "lineStyle": {"color": g.EJE, "type": "dashed"},
                             "label": {"show": False},
                             "data": [{"yAxis": 40}, {"xAxis": round(corte_valor / 1000)}]}
    grafico_plan = g.base(
        legend=g.leyenda(),
        tooltip={"trigger": "item", "confine": True, "formatter": "{@[2]}<br>Facturación: $ {@[0]}k<br>Riesgo: {@[1]}%"},
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
            {"label": "Riesgo alto", "valor": len(altos), "alerta": bool(altos), "detalle": "60% o más de probabilidad"},
            {"label": "Facturación en riesgo alto", "valor": formato_millones(sum(c["facturacion"] for c in altos)),
             "detalle": "anual"},
            {"label": "Pérdida esperada", "valor": formato_millones(esperada), "alerta": esperada > 0,
             "detalle": "facturación × probabilidad de abandono"},
            {"label": "Retener ya", "valor": len(retener), "alerta": bool(retener),
             "detalle": formato_millones(sum(c["facturacion"] for c in retener)) + " en juego"},
        ],
        "conclusiones": [
            f"{act[0]['nombre']} tiene la mayor probabilidad de abandono ({riesgo_abandono(act[0])}%): "
            f"lleva {act[0]['dias_sin_pedir']} días sin pedir.",
            f"{len(altos)} clientes están en riesgo alto, con {formato_millones(sum(c['facturacion'] for c in altos))} de facturación anual.",
            f"Si no se actúa, la pérdida esperada es de {formato_millones(esperada)} al año.",
            "La prioridad son los clientes «Retener ya»: "
            + ", ".join(c["nombre"] for c in retener) + "." if retener else "Ningún cliente valioso tiene riesgo alto.",
        ],
        "secciones": [
            seccion("Quiénes pueden dejar de pedir", grafico=grafico_riesgo, alto=420,
                    descripcion="Probabilidad de que cada cliente deje de pedir en los próximos 6 meses.", lectura=[
                        "Rojo: riesgo alto. Naranja: medio. Verde: bajo.",
                        "El modelo pondera días sin pedir (45%), caída de pedidos contra el año anterior (35%) y tendencia (20%).",
                    ]),
            seccion("Por qué están en riesgo", lectura=[
                "Las señales más fuertes son llevar muchos días sin pedir y haber hecho menos pedidos que el año anterior.",
            ], tabla={
                "titulo": "Señales de los clientes con más riesgo",
                "columnas": ["Cliente", "Riesgo", "Días sin pedir", "Pedidos vs año anterior", "Tendencia"],
                "filas": filas_senales,
            }),
            seccion("Qué hacer con cada cliente", grafico=grafico_plan, alto=420, acciones=acciones[:7], lectura=[
                "Arriba a la derecha están los que más importa retener: facturan mucho y tienen riesgo alto.",
                "Las líneas punteadas marcan la facturación mediana y el umbral de 40% de riesgo.",
            ]),
        ],
        "sugerencias": ["¿Por qué UTE tiene riesgo alto?", "Armame la agenda de visitas de esta semana",
                        "¿Qué le ofrezco a un cliente para reactivarlo?"],
        "contexto_ia": {"riesgos": {c["nombre"]: riesgo_abandono(c) for c in act},
                        "cuadrantes": {c["nombre"]: CUADRANTES[cuadrante(c)][0] for c in act}},
    }
