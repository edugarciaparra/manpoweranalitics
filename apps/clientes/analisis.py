"""
Análisis del módulo Clientes.

Cada análisis es una pantalla del menú. Los textos (sector, tipo, estado,
tendencia, ejecutivo) vienen de las tablas de referencia; acá no se nombra
ningún valor concreto. Todos los gráficos abren el detalle de clientes.
"""
from collections import Counter, defaultdict
from datetime import date

from apps.core import graficos as g
from apps.core.analisis import Catalogo, seccion
from apps.core.catalogos import catalogo as tabla_referencia
from apps.core.estadistica import mediana
from apps.core.utils import formato_millones, formato_numero, formato_pct

from . import services
from .services import ACTIVIDADES, ESTADO_ACTIVO_ID, LINEAS, ROLES_EJECUTIVO

catalogo = Catalogo()
FOTO = {"usa_periodo": False}

DIAS_BUCKETS = [("Menos de 30 días", 0, 30), ("31 a 90 días", 31, 90), ("91 a 180 días", 91, 180),
                ("181 días a 1 año", 181, 365), ("Más de 1 año", 366, 10 ** 6), ("Nunca pidió", None, None)]
ANTIG_BUCKETS = [("Menos de 1 año", 0, .99), ("1 a 3 años", 1, 2.99), ("3 a 5 años", 3, 4.99),
                 ("5 a 10 años", 5, 9.99), ("10 a 20 años", 10, 19.99), ("Más de 20 años", 20, 999)]
RIESGO_BUCKETS = [("Bajo (0–34)", 0, 34), ("Medio (35–59)", 35, 59), ("Alto (60+)", 60, 100)]


def _pct(a, b):
    return round(a / b * 100) if b else 0


def _bucket(valor, buckets):
    for etiq, a, b in buckets:
        if a is None and valor is None:
            return etiq
        if a is not None and valor is not None and a <= valor <= b:
            return etiq
    return buckets[-1][0]


def _barras_h(nombre, etiquetas, valores, color=None, formato="{c}", alto_barra=20, fmt_eje=None):
    opcion = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        grid={"left": 8, "right": 64, "top": 8, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores(fmt_eje),
        yAxis=g.eje_categorias(etiquetas, inverse=True),
        series=[g.barras(nombre, valores, color or g.SERIES[0], barMaxWidth=alto_barra,
                         itemStyle={"color": color or g.SERIES[0], "borderRadius": [0, 4, 4, 0]},
                         label={"show": True, "position": "right", "formatter": formato, "color": g.TINTA_SUAVE})],
    )
    if fmt_eje:
        opcion["tooltip"]["valueFormatter"] = fmt_eje
    return opcion


def _barras_v(nombre, etiquetas, valores, colores=None, rotar=0):
    datos = [{"value": v, "itemStyle": {"color": c}} for v, c in zip(valores, colores)] if colores else valores
    return g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        xAxis=g.eje_categorias(etiquetas, axisLabel={"interval": 0, "rotate": rotar, "color": g.TINTA_SUAVE}),
        yAxis=g.eje_valores(),
        series=[g.barras(nombre, datos, g.SERIES[0], label={"show": True, "position": "top", "color": g.TINTA_SUAVE})],
    )


# ==========================================================================
# 1. Composición de la cartera
# ==========================================================================
@catalogo.registrar(
    "composicion", "Composición de la cartera",
    "Cuántos clientes hay en cada estado, sector y tipo de cliente.",
    icono="bi-pie-chart", **FOTO,
)
def composicion(periodo):
    todos = services.clientes()
    act = services.activos()
    activo = services.estado_activo()

    # Estados en el orden de la tabla EstadosCliente
    tabla_estados = sorted(tabla_referencia("EstadosCliente").items())
    estados = [d for _, d in tabla_estados]
    por_estado = Counter(c["estado"] for c in todos)
    grafico_estado = _barras_v("Clientes", estados, [por_estado[e] for e in estados],
                               [g.SERIES[0] if i == ESTADO_ACTIVO_ID else g.AZUL[1] for i, _ in tabla_estados], rotar=25)

    sectores = Counter(c["sector"] for c in act).most_common()
    grafico_sector = _barras_h("Clientes activos", [s for s, _ in sectores], [v for _, v in sectores])

    tipos = Counter(c["tipo"] for c in act).most_common()
    grafico_tipo = _barras_h("Clientes activos", [t for t, _ in tipos], [v for _, v in tipos], g.SERIES[2])

    hoy = date.today()
    nuevos = [c for c in todos if c["fecha_ingreso"] and (hoy - c["fecha_ingreso"]).days <= 365]
    top3_sector = sum(v for _, v in sectores[:3])
    return {
        "kpis": [
            {"label": "Clientes registrados", "valor": formato_numero(len(todos)), "detalle": "en la tabla Clientes"},
            {"label": activo or "Activos", "valor": formato_numero(len(act)), "detalle": f"{_pct(len(act), len(todos))}% del total"},
            {"label": "Sector principal", "valor": sectores[0][0] if sectores else "—",
             "detalle": f"{_pct(sectores[0][1], len(act))}% de los activos" if sectores else ""},
            {"label": "Ingresaron en el último año", "valor": len(nuevos), "detalle": "clientes nuevos"},
        ],
        "conclusiones": [
            f"{_pct(len(act), len(todos))}% de los clientes registrados está en estado «{activo}».",
            f"Los 3 sectores principales reúnen el {_pct(top3_sector, len(act))}% de los clientes activos: "
            + ", ".join(s for s, _ in sectores[:3]) + ".",
            f"«{tipos[0][0]}» es el tipo de cliente más común ({_pct(tipos[0][1], len(act))}%)." if tipos else "",
            f"En el último año ingresaron {len(nuevos)} clientes.",
        ],
        "secciones": [
            seccion("Clientes por estado", grafico=grafico_estado, alto=280, detalle="estado",
                    ayuda_detalle="Hacé clic en una barra para ver los clientes de ese estado.",
                    explicacion="Cantidad de clientes en cada estado de la tabla EstadosCliente. En azul fuerte el estado "
                                "activo; el resto en celeste.",
                    lectura=[f"{formato_numero(len(todos) - len(act))} clientes no están activos."]),
            seccion("Clientes activos por sector", grafico=grafico_sector, alto=max(260, 30 * len(sectores)), detalle="sector",
                    ayuda_detalle="Hacé clic en un sector para ver sus clientes.",
                    explicacion="Ranking de sectores de actividad (tabla SectoresActividad) según la cantidad de clientes activos.",
                    lectura=[f"{sectores[0][0]} encabeza con {sectores[0][1]} clientes." if sectores else ""]),
            seccion("Clientes activos por tipo", grafico=grafico_tipo, alto=max(200, 40 * len(tipos)), detalle="tipo",
                    ayuda_detalle="Hacé clic en un tipo para ver sus clientes.",
                    explicacion="Cantidad de clientes activos según el tipo de cliente (tabla TiposCliente).",
                    lectura=[]),
        ],
        "sugerencias": ["¿En qué sectores tenemos poca presencia?", "¿Cuántos prospectos podemos convertir?"],
        "contexto_ia": {"por_estado": dict(por_estado), "sectores": dict(sectores), "tipos": dict(tipos)},
    }


# ==========================================================================
# 2. Concentración de la facturación
# ==========================================================================
@catalogo.registrar(
    "concentracion", "Concentración de la facturación",
    "Qué sectores y qué clientes explican la facturación, y cuánto depende de pocos clientes.",
    icono="bi-trophy", **FOTO,
)
def concentracion(periodo):
    act = services.activos()
    fact_sector = defaultdict(float)
    for c in act:
        fact_sector[c["sector"]] += c["facturado_12m"]
    sectores = sorted(((s, v) for s, v in fact_sector.items() if v > 0), key=lambda x: -x[1])
    grafico_sector = _barras_h("Facturado 12 meses", [s for s, _ in sectores], [round(v) for _, v in sectores],
                               formato="", fmt_eje="fmt:pesos_k")
    grafico_sector["series"][0]["label"]["show"] = False

    orden = sorted([c for c in act if c["facturado_12m"] > 0], key=lambda c: -c["facturado_12m"])
    total = sum(c["facturado_12m"] for c in orden)
    part = [round(c["facturado_12m"] / total * 100, 2) for c in orden] if total else []
    acum, s = [], 0
    for p_ in part:
        s += p_
        acum.append(round(s, 1))
    corte = next((i for i, a in enumerate(acum) if a >= 80), len(acum) - 1) + 1 if acum else 0
    ver = orden[:25]
    grafico_pareto = g.base(
        legend=g.leyenda(),
        tooltip={"trigger": "axis", "confine": True, "valueFormatter": "fmt:pct"},
        xAxis=g.eje_categorias([c["nombre"] for c in ver], axisLabel={"interval": 0, "rotate": 45, "color": g.TINTA_SUAVE}),
        yAxis=g.eje_valores("fmt:pct", max=100),
        grid={"left": 8, "right": 16, "top": 36, "bottom": 8, "containLabel": True},
        series=[
            g.barras("Participación", [{"value": p_, "itemStyle": {"color": g.SERIES[0] if i < corte else g.AZUL[1]}}
                                       for i, p_ in enumerate(part[:25])]),
            g.linea("Acumulado", acum[:25], g.SERIES[1],
                    markLine={"silent": True, "symbol": "none", "lineStyle": {"color": g.TINTA_SUAVE, "type": "dashed"},
                              "label": {"formatter": "80%", "color": g.TINTA_SUAVE}, "data": [{"yAxis": 80}]}),
        ],
    )
    sin_fact = len(act) - len(orden)
    return {
        "kpis": [
            {"label": "Facturado 12 meses", "valor": formato_millones(total), "detalle": f"{len(orden)} clientes con facturación"},
            {"label": "Clientes que hacen el 80%", "valor": corte, "detalle": f"de {len(orden)} que facturan"},
            {"label": "Peso del principal", "valor": formato_pct(part[0]) if part else "—", "alerta": bool(part) and part[0] > 20,
             "detalle": orden[0]["nombre"] if orden else ""},
            {"label": "Activos sin facturar", "valor": sin_fact, "alerta": sin_fact > 0, "detalle": "en los últimos 12 meses"},
        ],
        "conclusiones": [
            f"{corte} clientes explican el 80% de lo facturado en los últimos 12 meses.",
            f"{sectores[0][0]} es el sector que más factura ({_pct(sectores[0][1], total)}% del total)." if sectores else "",
            f"{orden[0]['nombre']} es el cliente que más factura ({formato_pct(part[0])} del total)." if orden else "",
            f"{sin_fact} clientes activos no facturaron nada en los últimos 12 meses.",
        ],
        "secciones": [
            seccion("Facturación por sector", grafico=grafico_sector, alto=max(260, 30 * len(sectores)), detalle="sector",
                    ayuda_detalle="Hacé clic en un sector para ver sus clientes.",
                    explicacion="Lo facturado en los últimos 12 meses (OrdenesFacturacion) por los clientes activos de cada "
                                "sector (tabla SectoresActividad).", lectura=[]),
            seccion("Concentración por cliente", grafico=grafico_pareto, alto=380, detalle="cliente",
                    ayuda_detalle="Hacé clic en un cliente para ver su ficha.",
                    explicacion="Los 25 clientes que más facturaron, de mayor a menor. Las barras son la participación de "
                                "cada uno y la línea el acumulado; en azul fuerte los que juntos llegan al 80%.",
                    lectura=[f"Los primeros {min(corte, 25)} clientes concentran el {acum[min(corte, 25) - 1]}%." if acum else ""]),
        ],
        "sugerencias": ["¿Cuánto riesgo tenemos con el cliente principal?", "¿Qué sectores conviene desarrollar?"],
        "contexto_ia": {"facturado_por_sector": dict(sectores), "clientes_80": corte,
                        "top5": {c["nombre"]: c["facturado_12m"] for c in orden[:5]}},
    }


# ==========================================================================
# 3. Penetración y oportunidad
# ==========================================================================
@catalogo.registrar(
    "penetracion", "Penetración y oportunidad",
    "Qué parte de la dotación de cada cliente es personal Manpower y dónde hay más lugar para crecer.",
    icono="bi-bullseye", **FOTO,
)
def penetracion(periodo):
    act = [c for c in services.activos() if c["asociados_total"] > 0]
    puntos = [{"name": c["nombre"], "value": [c["asociados_total"], c["penetracion"], c["asociados_mp"]],
               "itemStyle": {"color": g.SERIES[0] if c["usa_temporal"] else g.NEUTRO}} for c in act]
    grafico_disp = g.base(
        tooltip={"trigger": "item", "confine": True,
                 "formatter": "{b}<br>Dotación total: {@[0]}<br>Personal Manpower: {@[2]} ({@[1]}%)"},
        grid={"left": 36, "right": 24, "top": 24, "bottom": 40, "containLabel": True},
        xAxis=g.eje_valores("fmt:num", name="Dotación total del cliente (escala logarítmica)", nameLocation="middle",
                            nameGap=30, type="log", splitLine={"show": False}),
        yAxis=g.eje_valores("fmt:pct", name="% de personal Manpower", nameLocation="middle", nameGap=44, max=100),
        series=[{"type": "scatter", "symbolSize": 10, "data": puntos, "itemStyle": {"opacity": .8}}],
    )
    oport = sorted([c for c in act if c["usa_temporal"]], key=lambda c: -(c["asociados_total"] - c["asociados_mp"]))[:15]
    grafico_oport = _barras_h("Dotación sin cubrir", [c["nombre"] for c in oport],
                              [c["asociados_total"] - c["asociados_mp"] for c in oport], g.SERIES[1])
    con_mp = [c for c in act if c["asociados_mp"] > 0]
    med = mediana([c["penetracion"] for c in con_mp]) if con_mp else 0
    sin_mp_temporal = [c for c in act if c["asociados_mp"] == 0 and c["usa_temporal"]]
    total_mp = sum(c["asociados_mp"] for c in act)
    return {
        "kpis": [
            {"label": "Personal Manpower", "valor": formato_numero(total_mp), "detalle": "en clientes activos"},
            {"label": "Penetración mediana", "valor": formato_pct(med), "detalle": "entre clientes con personal Manpower"},
            {"label": "Usan temporales sin Manpower", "valor": len(sin_mp_temporal), "alerta": bool(sin_mp_temporal),
             "detalle": "oportunidad directa"},
            {"label": "Mayor oportunidad", "valor": oport[0]["nombre"] if oport else "—",
             "detalle": f"{formato_numero(oport[0]['asociados_total'] - oport[0]['asociados_mp'])} puestos sin cubrir" if oport else ""},
        ],
        "conclusiones": [
            f"En el cliente típico, el personal Manpower es el {formato_pct(med)} de su dotación.",
            f"{len(sin_mp_temporal)} clientes activos dicen usar personal temporal pero no tienen asociados Manpower.",
            f"{oport[0]['nombre']} es la mayor oportunidad: {formato_numero(oport[0]['asociados_total'] - oport[0]['asociados_mp'])} "
            "personas que no son de Manpower." if oport else "",
            "Los clientes grandes con baja penetración son los que más pueden crecer sin salir a buscar clientes nuevos.",
        ],
        "secciones": [
            seccion("Dotación y penetración de cada cliente", grafico=grafico_disp, alto=420, detalle="cliente",
                    ayuda_detalle="Hacé clic en un punto para ver la ficha del cliente.",
                    explicacion="Cada punto es un cliente activo. Hacia la derecha, más empleados en total; hacia arriba, mayor "
                                "porcentaje de personal Manpower (ClienteCantidadAsociadosManpow sobre "
                                "ClienteCantidadAsociadosTotal). En azul los que declaran usar personal temporal.",
                    lectura=["Abajo a la derecha están los clientes grandes con poca presencia de Manpower: la mayor oportunidad."]),
            seccion("Dónde hay más lugar para crecer", grafico=grafico_oport, alto=440, detalle="cliente",
                    ayuda_detalle="Hacé clic en un cliente para ver su ficha.",
                    explicacion="Los 15 clientes que usan personal temporal con más empleados que no son de Manpower "
                                "(dotación total menos asociados Manpower).",
                    lectura=[]),
        ],
        "sugerencias": ["¿Qué clientes grandes tienen poca penetración?", "¿Cómo crecer en los clientes actuales?"],
        "contexto_ia": {"penetracion_mediana": med, "sin_manpower_con_temporal": len(sin_mp_temporal),
                        "oportunidades": {c["nombre"]: c["asociados_total"] - c["asociados_mp"] for c in oport[:5]}},
    }


# ==========================================================================
# 4. Actividad y clientes dormidos
# ==========================================================================
@catalogo.registrar(
    "actividad", "Actividad y clientes dormidos",
    "Hace cuánto pidió cada cliente activo y quiénes están pidiendo más o menos que el año anterior.",
    icono="bi-activity", **FOTO,
)
def actividad(periodo):
    act = services.activos()
    etiq = [e for e, _, _ in DIAS_BUCKETS]
    por_dias = Counter(_bucket(c["dias_sin_pedir"], DIAS_BUCKETS) for c in act)
    colores = [g.AZUL[5], g.AZUL[3], g.AZUL[1], g.NARANJA[2], g.NARANJA[4], g.NEUTRO]
    grafico_dias = _barras_v("Clientes activos", etiq, [por_dias[e] for e in etiq], colores, rotar=15)

    def variacion(c):
        if c["pedidos_prev"] == 0:
            return "Nuevos o sin historia" if c["pedidos_12m"] else "Sin pedidos"
        cambio = (c["pedidos_12m"] - c["pedidos_prev"]) / c["pedidos_prev"]
        return "Crecen" if cambio > .1 else "Bajan" if cambio < -.1 else "Estables"
    grupos = ["Crecen", "Estables", "Bajan", "Nuevos o sin historia", "Sin pedidos"]
    por_var = Counter(variacion(c) for c in act)
    grafico_var = _barras_v("Clientes activos", grupos, [por_var[x] for x in grupos],
                            [g.POSITIVO, g.AZUL[2], g.NEGATIVO, g.SERIES[2], g.NEUTRO])
    dormidos = [c for c in act if c["dias_sin_pedir"] is None or c["dias_sin_pedir"] > 90]
    fact_dormidos = sum(c["facturado_prev"] for c in dormidos)
    return {
        "kpis": [
            {"label": "Pidieron en los últimos 30 días", "valor": por_dias[etiq[0]], "detalle": f"de {len(act)} activos"},
            {"label": "Dormidos", "valor": len(dormidos), "alerta": bool(dormidos), "detalle": "más de 90 días sin pedir"},
            {"label": "Piden menos que el año pasado", "valor": por_var["Bajan"], "alerta": por_var["Bajan"] > por_var["Crecen"],
             "detalle": "más de 10% de caída"},
            {"label": "Facturaban el año anterior", "valor": formato_millones(fact_dormidos), "detalle": "los clientes dormidos"},
        ],
        "conclusiones": [
            f"{len(dormidos)} clientes activos llevan más de 90 días sin pedir.",
            f"{por_var['Crecen']} clientes piden más que el año pasado y {por_var['Bajan']} piden menos.",
            f"Los clientes dormidos facturaron {formato_millones(fact_dormidos)} el año anterior: recuperarlos es la prioridad comercial.",
            f"{por_dias['Nunca pidió']} clientes activos nunca hicieron un pedido." if por_dias["Nunca pidió"] else "",
        ],
        "secciones": [
            seccion("Hace cuánto pidió cada cliente", grafico=grafico_dias, alto=300, detalle="dias",
                    ayuda_detalle="Hacé clic en una barra para ver esos clientes.",
                    explicacion="Clientes activos agrupados por los días desde su último pedido (tabla Pedidos). En azul los "
                                "que pidieron hace poco y en naranja los que llevan mucho tiempo sin pedir.",
                    lectura=[]),
            seccion("Pedidos de este año contra el anterior", grafico=grafico_var, alto=300, detalle="variacion",
                    ayuda_detalle="Hacé clic en una barra para ver esos clientes.",
                    explicacion="Compara los pedidos de los últimos 12 meses con los 12 anteriores. «Crecen» y «Bajan» son "
                                "variaciones de más de 10%.",
                    lectura=[]),
        ],
        "sugerencias": ["¿A qué clientes dormidos llamo primero?", "¿Por qué bajan los pedidos?"],
        "contexto_ia": {"por_dias": dict(por_dias), "variacion": dict(por_var), "dormidos": len(dormidos)},
    }


# ==========================================================================
# 5. Antigüedad y tendencia
# ==========================================================================
@catalogo.registrar(
    "antiguedad", "Antigüedad y tendencia",
    "Desde cuándo son clientes, cuántos ingresan por año y cuál es su tendencia declarada.",
    icono="bi-calendar3", **FOTO,
)
def antiguedad(periodo):
    todos = services.clientes()
    act = services.activos()
    hoy = date.today()
    anios = list(range(hoy.year - 9, hoy.year + 1))
    altas = Counter(c["fecha_ingreso"].year for c in todos if c["fecha_ingreso"])
    grafico_altas = _barras_v("Clientes nuevos", [str(a) for a in anios], [altas[a] for a in anios])

    etiq = [e for e, _, _ in ANTIG_BUCKETS]
    por_antig = Counter(_bucket(c["antiguedad"], ANTIG_BUCKETS) for c in act)
    grafico_antig = _barras_v("Clientes activos", etiq, [por_antig[e] for e in etiq],
                              [g.AZUL[i] for i in (1, 2, 3, 4, 5, 6)], rotar=15)

    tend = [d for _, d in sorted(tabla_referencia("Tendencias").items())]
    por_tend = Counter(c["tendencia"] for c in act)
    grafico_tend = _barras_v("Clientes activos", tend, [por_tend[t] for t in tend])
    prom = sum(altas[a] for a in anios[:-1]) / max(1, len(anios) - 1)
    return {
        "kpis": [
            {"label": "Antigüedad mediana", "valor": f"{mediana([c['antiguedad'] for c in act]):.1f} años".replace(".", ","),
             "detalle": "de los clientes activos"},
            {"label": f"Nuevos en {hoy.year}", "valor": altas[hoy.year], "detalle": f"promedio anual {prom:.0f}"},
            {"label": "Más de 10 años", "valor": sum(1 for c in act if c["antiguedad"] >= 10), "detalle": "clientes históricos"},
            {"label": "Tendencia más declarada", "valor": por_tend.most_common(1)[0][0] if por_tend else "—", "detalle": "campo TendenciaId"},
        ],
        "conclusiones": [
            f"El cliente activo típico trabaja con Manpower hace {mediana([c['antiguedad'] for c in act]):.1f} años.".replace(".", ",", 1),
            f"En {hoy.year} ingresaron {altas[hoy.year]} clientes, contra un promedio de {prom:.0f} por año.",
            f"{sum(1 for c in act if c['antiguedad'] < 1)} clientes activos tienen menos de un año: conviene acompañarlos de cerca.",
            "La tendencia la carga el ejecutivo; conviene contrastarla con la actividad real de pedidos.",
        ],
        "secciones": [
            seccion("Clientes nuevos por año", grafico=grafico_altas, alto=280, detalle="anio",
                    ayuda_detalle="Hacé clic en un año para ver los clientes que ingresaron.",
                    explicacion="Cantidad de clientes según el año de ClienteFechaIngreso, últimos 10 años.", lectura=[]),
            seccion("Antigüedad de los clientes activos", grafico=grafico_antig, alto=280, detalle="antiguedad",
                    ayuda_detalle="Hacé clic en una barra para ver esos clientes.",
                    explicacion="Años desde el ingreso de cada cliente activo. Más oscuro, más antiguo.", lectura=[]),
            seccion("Tendencia declarada", grafico=grafico_tend, alto=260, detalle="tendencia",
                    ayuda_detalle="Hacé clic en una barra para ver esos clientes.",
                    explicacion="Clientes activos según la tendencia cargada en la ficha (tabla Tendencias).", lectura=[]),
        ],
        "sugerencias": ["¿Retenemos a los clientes nuevos?", "¿La tendencia coincide con los pedidos reales?"],
        "contexto_ia": {"altas_por_anio": {str(a): altas[a] for a in anios}, "tendencias": dict(por_tend)},
    }


# ==========================================================================
# 6. Líneas de servicio
# ==========================================================================
@catalogo.registrar(
    "servicios", "Líneas de servicio",
    "Qué líneas opera cada cliente y cuántos trabajan con una sola: la oportunidad de venta cruzada.",
    icono="bi-diagram-3", **FOTO,
)
def servicios(periodo):
    act = services.activos()
    pct = {nombre: _pct(sum(c[campo] for c in act), len(act)) for nombre, campo in LINEAS.items()}
    orden = sorted(pct.items(), key=lambda x: -x[1])
    grafico_lineas = _barras_h("Clientes", [n for n, _ in orden], [v for _, v in orden], formato="{c}%", fmt_eje="fmt:pct")
    grafico_lineas["xAxis"]["max"] = 100

    cant = Counter(len(c["lineas"]) for c in act)
    etiq = [str(n) for n in range(len(LINEAS) + 1)]
    grafico_cant = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        xAxis=g.eje_categorias([f"{n} línea{'s' if n != '1' else ''}" for n in etiq]),
        yAxis=g.eje_valores(),
        series=[g.barras("Clientes", [{"value": cant[int(n)], "itemStyle": {"color": g.NARANJA[3] if n == "1" else g.SERIES[0]}}
                                      for n in etiq], label={"show": True, "position": "top", "color": g.TINTA_SUAVE})],
    )
    una = cant[1]
    temporal = _pct(sum(c["usa_temporal"] for c in act), len(act))
    return {
        "kpis": [
            {"label": "Línea más usada", "valor": orden[0][0], "detalle": f"{orden[0][1]}% de los activos"},
            {"label": "Una sola línea", "valor": una, "alerta": _pct(una, len(act)) > 40, "detalle": f"{_pct(una, len(act))}% de los activos"},
            {"label": "Tres líneas o más", "valor": sum(v for k, v in cant.items() if k >= 3), "detalle": "clientes integrales"},
            {"label": "Usan personal temporal", "valor": f"{temporal}%", "detalle": "según la ficha"},
        ],
        "conclusiones": [
            f"«{orden[0][0]}» es la línea más usada ({orden[0][1]}%) y «{orden[-1][0]}» la menos usada ({orden[-1][1]}%).",
            f"{una} clientes ({_pct(una, len(act))}%) trabajan con una sola línea: son el objetivo de la venta cruzada.",
            f"{temporal}% de los clientes activos declara usar personal temporal.",
            "Un cliente con varias líneas es más difícil de perder: sumar una línea mejora la retención.",
        ],
        "secciones": [
            seccion("Qué líneas operan los clientes", grafico=grafico_lineas, alto=240, detalle="linea",
                    ayuda_detalle="Hacé clic en una línea para ver los clientes que la operan.",
                    explicacion="Porcentaje de clientes activos que opera cada línea de servicio (campos ClienteOpera…). "
                                "Un cliente puede operar varias.", lectura=[]),
            seccion("Cuántas líneas opera cada cliente", grafico=grafico_cant, alto=280, detalle="lineas",
                    ayuda_detalle="Hacé clic en una barra para ver esos clientes.",
                    explicacion="Clientes activos según la cantidad de líneas que operan. En naranja los de una sola línea.",
                    lectura=[]),
        ],
        "sugerencias": ["¿Qué línea ofrecer a los clientes de una sola línea?", "¿Qué sectores usan más RPO?"],
        "contexto_ia": {"porcentaje_por_linea": pct, "cantidad_de_lineas": dict(cant)},
    }


# ==========================================================================
# 7. Cartera por ejecutivo
# ==========================================================================
@catalogo.registrar(
    "ejecutivos", "Cartera por ejecutivo",
    "Cuántos clientes atiende cada ejecutivo, en qué líneas y cuánto facturan sus clientes.",
    icono="bi-person-badge", **FOTO,
)
def ejecutivos(periodo):
    act = services.activos()
    por_ejec = defaultdict(lambda: Counter())
    fact = defaultdict(float)
    clientes_ejec = defaultdict(set)
    for c in act:
        for rol, nombre in c["ejecutivos"].items():
            por_ejec[nombre][rol] += 1
            clientes_ejec[nombre].add(c["id"])
        for nombre in set(c["ejecutivos"].values()):
            fact[nombre] += c["facturado_12m"]
    nombres = sorted(clientes_ejec, key=lambda n: -len(clientes_ejec[n]))
    roles = list(ROLES_EJECUTIVO)
    grafico_roles = g.base(
        legend=g.leyenda(data=roles),
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        grid={"left": 8, "right": 16, "top": 36, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores(), yAxis=g.eje_categorias(nombres, inverse=True),
        series=[{"name": rol, "type": "bar", "stack": "r", "barMaxWidth": 22,
                 "data": [por_ejec[n][rol] for n in nombres], "itemStyle": {"color": g.SERIES[i]}}
                for i, rol in enumerate(roles)],
    )
    orden_f = sorted(fact.items(), key=lambda x: -x[1])
    grafico_fact = _barras_h("Facturado 12 meses", [n for n, _ in orden_f], [round(v) for _, v in orden_f],
                             g.SERIES[2], formato="", fmt_eje="fmt:pesos_k")
    grafico_fact["series"][0]["label"]["show"] = False
    sin_ejec = sum(1 for c in act if not c["ejecutivos"])
    cargas = [len(clientes_ejec[n]) for n in nombres]
    return {
        "kpis": [
            {"label": "Ejecutivos con cartera", "valor": len(nombres), "detalle": "en clientes activos"},
            {"label": "Clientes por ejecutivo", "valor": round(mediana(cargas)) if cargas else 0, "detalle": "mediana"},
            {"label": "Mayor cartera", "valor": nombres[0] if nombres else "—", "detalle": f"{cargas[0]} clientes" if cargas else ""},
            {"label": "Clientes sin ejecutivo", "valor": sin_ejec, "alerta": sin_ejec > 0, "detalle": "activos sin asignar"},
        ],
        "conclusiones": [
            f"{nombres[0]} tiene la cartera más grande ({cargas[0]} clientes) y {nombres[-1]} la más chica ({cargas[-1]})." if nombres else "",
            f"Los clientes de {orden_f[0][0]} son los que más facturan ({formato_millones(orden_f[0][1])})." if orden_f else "",
            f"{sin_ejec} clientes activos no tienen ningún ejecutivo asignado." if sin_ejec else "Todos los clientes activos tienen ejecutivo.",
            "Un cliente puede tener un ejecutivo distinto por línea: la suma por ejecutivo puede superar el total de clientes.",
        ],
        "secciones": [
            seccion("Clientes por ejecutivo y línea", grafico=grafico_roles, alto=max(280, 34 * len(nombres)), detalle="ejecutivo",
                    ayuda_detalle="Hacé clic en una barra para ver los clientes de ese ejecutivo en esa línea.",
                    explicacion="Cantidad de clientes activos que atiende cada ejecutivo (tabla de ejecutivos), partida por "
                                "la línea en la que está asignado (ClienteRpoEjecutivoId, ClientePrmEjecutivoId, etc.).",
                    lectura=[]),
            seccion("Facturación de la cartera de cada ejecutivo", grafico=grafico_fact, alto=max(260, 34 * len(orden_f)),
                    detalle="ejecutivo", ayuda_detalle="Hacé clic en un ejecutivo para ver sus clientes.",
                    explicacion="Lo facturado en los últimos 12 meses por los clientes que atiende cada ejecutivo, en "
                                "cualquier línea.", lectura=[]),
        ],
        "sugerencias": ["¿La carga está bien repartida?", "¿Quién debería atender los clientes sin ejecutivo?"],
        "contexto_ia": {"clientes_por_ejecutivo": {n: len(clientes_ejec[n]) for n in nombres},
                        "facturado_por_ejecutivo": dict(orden_f)},
    }


# ==========================================================================
# 8. Riesgo de abandono
# ==========================================================================
def riesgo(c):
    """Probabilidad estimada (0-100) de que el cliente deje de pedir: combina días sin pedir (60%)
    y caída de pedidos contra el año anterior (40%). Solo usa datos, no la tendencia declarada."""
    dias = c["dias_sin_pedir"]
    inactividad = 1 if dias is None else min(dias / 270, 1)
    caida = 0
    if c["pedidos_prev"]:
        caida = max(0, min(1, (c["pedidos_prev"] - c["pedidos_12m"]) / c["pedidos_prev"]))
    return round((inactividad * .6 + caida * .4) * 100)


@catalogo.registrar(
    "abandono", "Riesgo de abandono",
    "Qué clientes activos pueden dejar de pedir y cuánta facturación está en juego.",
    icono="bi-person-x", **FOTO,
)
def abandono(periodo):
    act = [c for c in services.activos() if c["pedidos_prev"] or c["pedidos_12m"]]
    etiq = [e for e, _, _ in RIESGO_BUCKETS]
    por_riesgo = Counter(_bucket(riesgo(c), RIESGO_BUCKETS) for c in act)
    grafico_dist = _barras_v("Clientes", etiq, [por_riesgo[e] for e in etiq],
                             [g.ESTADO["bien"], g.ESTADO["serio"], g.ESTADO["critico"]])
    top = sorted(act, key=lambda c: (-riesgo(c), -c["facturado_prev"]))[:15]

    def color(r):
        return g.ESTADO["critico"] if r >= 60 else g.ESTADO["serio"] if r >= 35 else g.ESTADO["bien"]
    grafico_top = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        grid={"left": 8, "right": 56, "top": 8, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores("fmt:pct", max=100), yAxis=g.eje_categorias([c["nombre"] for c in top], inverse=True),
        series=[{"name": "Riesgo", "type": "bar", "barMaxWidth": 20,
                 "data": [{"value": riesgo(c), "itemStyle": {"color": color(riesgo(c)), "borderRadius": [0, 4, 4, 0]}} for c in top],
                 "label": {"show": True, "position": "right", "formatter": "{c}%", "color": g.TINTA_SUAVE}}],
    )
    altos = [c for c in act if riesgo(c) >= 60]
    en_juego = sum(c["facturado_prev"] for c in altos)
    esperada = sum(c["facturado_prev"] * riesgo(c) / 100 for c in act)
    return {
        "kpis": [
            {"label": "Riesgo alto", "valor": len(altos), "alerta": bool(altos), "detalle": "60 o más sobre 100"},
            {"label": "Riesgo medio", "valor": por_riesgo[etiq[1]], "detalle": "entre 35 y 59"},
            {"label": "Facturación en juego", "valor": formato_millones(en_juego), "detalle": "del año anterior, riesgo alto"},
            {"label": "Pérdida esperada", "valor": formato_millones(esperada), "detalle": "facturación × probabilidad"},
        ],
        "conclusiones": [
            f"{len(altos)} clientes activos tienen riesgo alto de dejar de pedir.",
            f"Esos clientes facturaron {formato_millones(en_juego)} el año anterior.",
            f"{top[0]['nombre']} es el caso más urgente (riesgo {riesgo(top[0])}%)." if top else "",
            "El riesgo combina días sin pedir (60%) y caída de pedidos contra el año anterior (40%).",
        ],
        "secciones": [
            seccion("Cómo se reparte el riesgo", grafico=grafico_dist, alto=260, detalle="riesgo",
                    ayuda_detalle="Hacé clic en una barra para ver esos clientes.",
                    explicacion="Clientes activos con historia de pedidos, agrupados por su puntaje de riesgo: verde bajo, "
                                "naranja medio, rojo alto.", lectura=[]),
            seccion("Los 15 clientes con más riesgo", grafico=grafico_top, alto=460, detalle="cliente",
                    ayuda_detalle="Hacé clic en un cliente para ver su ficha.",
                    explicacion="Ordenados por riesgo y, a igual riesgo, por lo que facturaban el año anterior.", lectura=[]),
        ],
        "sugerencias": [f"¿Qué pasó con {top[0]['nombre']}?" if top else "¿Qué clientes están en riesgo?",
                        "¿Cómo reactivar a un cliente dormido?"],
        "contexto_ia": {"por_riesgo": dict(por_riesgo), "top": {c["nombre"]: riesgo(c) for c in top[:8]}},
    }


# ==========================================================================
# Detalle de clientes (modal)
# ==========================================================================
def _filtro(clave, valor, serie):
    es_activo = services.es_activo
    if clave == "estado":
        return f"Clientes en estado «{valor}»", lambda c: c["estado"] == valor
    if clave == "sector":
        return f"Sector: {valor}", lambda c: es_activo(c) and c["sector"] == valor
    if clave == "tipo":
        return f"Tipo: {valor}", lambda c: es_activo(c) and c["tipo"] == valor
    if clave == "cliente":
        return valor, lambda c: c["nombre"] == valor
    if clave == "dias":
        return f"Último pedido: {valor.lower()}", lambda c: es_activo(c) and _bucket(c["dias_sin_pedir"], DIAS_BUCKETS) == valor
    if clave == "variacion":
        def var(c):
            if c["pedidos_prev"] == 0:
                return "Nuevos o sin historia" if c["pedidos_12m"] else "Sin pedidos"
            x = (c["pedidos_12m"] - c["pedidos_prev"]) / c["pedidos_prev"]
            return "Crecen" if x > .1 else "Bajan" if x < -.1 else "Estables"
        return f"Clientes que {valor.lower()}" if valor in ("Crecen", "Bajan") else valor, lambda c: es_activo(c) and var(c) == valor
    if clave == "anio":
        return f"Ingresaron en {valor}", lambda c: c["fecha_ingreso"] and str(c["fecha_ingreso"].year) == valor
    if clave == "antiguedad":
        return f"Antigüedad: {valor.lower()}", lambda c: es_activo(c) and _bucket(c["antiguedad"], ANTIG_BUCKETS) == valor
    if clave == "tendencia":
        return f"Tendencia: {valor}", lambda c: es_activo(c) and c["tendencia"] == valor
    if clave == "linea":
        campo = LINEAS.get(valor)
        return f"Operan la línea {valor}", lambda c: es_activo(c) and campo is not None and c[campo]
    if clave == "lineas":
        n = int(valor.split()[0]) if valor[:1].isdigit() else -1
        return f"Clientes con {valor}", lambda c: es_activo(c) and len(c["lineas"]) == n
    if clave == "ejecutivo":
        if serie in ROLES_EJECUTIVO:
            return f"{valor} · línea {serie}", lambda c: es_activo(c) and c["ejecutivos"].get(serie) == valor
        return f"Clientes de {valor}", lambda c: es_activo(c) and valor in c["ejecutivos"].values()
    if clave == "riesgo":
        return f"Riesgo {valor.lower()}", lambda c: es_activo(c) and (c["pedidos_prev"] or c["pedidos_12m"]) and \
            _bucket(riesgo(c), RIESGO_BUCKETS) == valor
    return "Clientes", lambda c: False


PILDORAS_ACTIVIDAD = dict(zip(ACTIVIDADES, ["verde", "naranja", "gris"]))


@catalogo.detalle("composicion")
@catalogo.detalle("concentracion")
@catalogo.detalle("penetracion")
@catalogo.detalle("actividad")
@catalogo.detalle("antiguedad")
@catalogo.detalle("servicios")
@catalogo.detalle("ejecutivos")
@catalogo.detalle("abandono")
def detalle(clave, valor, serie, periodo):
    titulo, coincide = _filtro(clave, valor, serie)
    elegidos = sorted((c for c in services.clientes() if coincide(c)), key=lambda c: -c["facturado_12m"])
    por_act = Counter(services.actividad(c) for c in elegidos)
    return {
        "titulo": titulo,
        "descripcion": "ordenados por facturación de los últimos 12 meses",
        "columnas": services.COLUMNAS_DETALLE,
        "filas": [services.fila_detalle(c) for c in elegidos],
        "pildoras": {"Actividad": PILDORAS_ACTIVIDAD},
        "resumen": [{"texto": a, "valor": por_act.get(a, 0), "color": PILDORAS_ACTIVIDAD[a]} for a in ACTIVIDADES],
        "columna_resumen": "Actividad",
        "columna_avatar": "Cliente",
    }


# Pantallas de clientes migradas de la analítica del SGO
from . import analisis_sgo  # noqa: E402,F401
