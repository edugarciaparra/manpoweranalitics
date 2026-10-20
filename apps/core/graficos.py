"""
Helpers para armar opciones de ECharts con el mismo estilo en todos los análisis.

Las opciones se arman en Python como dicts y se mandan al navegador en JSON.
Como en JSON no se pueden pasar funciones, los formatos de números se indican
con textos especiales que static/js/analisis.js reemplaza por funciones:

    "fmt:pesos"    $ 1.234.567
    "fmt:pesos_k"  $ 1.235k
    "fmt:pct"      45%
    "fmt:num"      1.234
"""

# Paleta categórica en orden fijo (validada para daltonismo en pares adyacentes)
SERIES = ["#0B5CAB", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]

# Rampas secuenciales de un solo tono, de claro a oscuro
AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
NARANJA = ["#fde3d6", "#f8bfa3", "#f29a72", "#eb6834", "#c9521f", "#a03f17", "#7a2f10"]

# Divergente: positivo / negativo con gris en el medio
POSITIVO, NEGATIVO, NEUTRO = "#0B5CAB", "#E1251B", "#c3c2b7"

# Estados (siempre acompañados de texto o ícono)
ESTADO = {"bien": "#0ca30c", "atencion": "#fab219", "serio": "#ec835a", "critico": "#d03b3b"}

TINTA = "#14213D"
TINTA_SUAVE = "#5B6577"
GRILLA = "#E7EAF0"
EJE = "#C3C8D2"


def base(**extra):
    """Opción base: tooltip, grilla y colores comunes."""
    opcion = {
        "color": SERIES,
        "animationDuration": 500,
        "textStyle": {"fontFamily": "Inter, system-ui, sans-serif", "fontSize": 12, "color": TINTA_SUAVE},
        "tooltip": {"trigger": "axis", "confine": True},
        "grid": {"left": 8, "right": 16, "top": 36, "bottom": 8, "containLabel": True},
    }
    opcion.update(extra)
    return opcion


def eje_categorias(datos, **extra):
    eje = {
        "type": "category",
        "data": datos,
        "axisLine": {"lineStyle": {"color": EJE}},
        "axisTick": {"show": False},
        "axisLabel": {"color": TINTA_SUAVE},
    }
    eje.update(extra)
    return eje


def eje_valores(formato=None, **extra):
    eje = {
        "type": "value",
        "splitLine": {"lineStyle": {"color": GRILLA}},
        "axisLabel": {"color": TINTA_SUAVE},
    }
    # Por defecto, miles con punto (1.000) como se usa en Uruguay
    eje["axisLabel"]["formatter"] = formato or "fmt:num"
    eje.update(extra)
    return eje


def leyenda(**extra):
    l = {"top": 0, "left": 0, "icon": "roundRect", "itemWidth": 12, "itemHeight": 12,
         "textStyle": {"color": TINTA_SUAVE}}
    l.update(extra)
    return l


def barras(nombre, valores, color=None, **extra):
    s = {
        "name": nombre,
        "type": "bar",
        "data": valores,
        "barMaxWidth": 36,
        "itemStyle": {"borderRadius": [4, 4, 0, 0]},
    }
    if color:
        s["itemStyle"]["color"] = color
    s.update(extra)
    return s


def linea(nombre, valores, color=None, **extra):
    s = {
        "name": nombre,
        "type": "line",
        "data": valores,
        "smooth": 0.25,
        "symbolSize": 8,
        "lineStyle": {"width": 2},
    }
    if color:
        s["itemStyle"] = {"color": color}
        s["lineStyle"]["color"] = color
    s.update(extra)
    return s


def serie_pronostico(historia, prono, etiquetas_hist, etiquetas_futuras, nombre="Real",
                     formato=None):
    """Gráfico de línea con historia, proyección punteada y banda de confianza."""
    n_hist = len(historia)
    nada = [None] * n_hist
    puente = [None] * (n_hist - 1) + [historia[-1]]

    inferior = nada + prono["inferior"]
    ancho = nada + [s - i for s, i in zip(prono["superior"], prono["inferior"])]

    opcion = base(
        legend=leyenda(data=[nombre, "Proyección", "Rango probable (80%)"]),
        xAxis=eje_categorias(etiquetas_hist + etiquetas_futuras, boundaryGap=False),
        yAxis=eje_valores(formato),
        series=[
            {"name": "_base", "type": "line", "data": inferior, "stack": "banda",
             "lineStyle": {"opacity": 0}, "symbol": "none", "silent": True,
             "tooltip": {"show": False}},
            {"name": "Rango probable (80%)", "type": "line", "data": ancho, "stack": "banda",
             "lineStyle": {"opacity": 0}, "symbol": "none",
             "areaStyle": {"color": "rgba(11,92,171,.14)"}, "itemStyle": {"color": "rgba(11,92,171,.35)"},
             "tooltip": {"show": False}},
            linea(nombre, historia + [None] * len(prono["valores"]), SERIES[0]),
            linea("Proyección", puente + prono["valores"], SERIES[0],
                  lineStyle={"width": 2, "type": "dashed", "color": SERIES[0]},
                  symbol="emptyCircle"),
        ],
    )
    if formato:
        opcion["tooltip"]["valueFormatter"] = formato
    return opcion


# ---------------------------------------------------------------------------
# Gráficos rápidos a partir de filas de una consulta (pantallas del SGO)
# ---------------------------------------------------------------------------
def alto_ranking(n, minimo=260):
    """Alto en px para un ranking horizontal de n barras."""
    return max(minimo, 28 * n + 50)


def ranking(etiquetas, valores, nombre="Cantidad", color=None, formato=None):
    """Barras horizontales, la primera arriba."""
    return base(
        tooltip={"trigger": "axis", "axisPointer": {"type": "shadow"}, "confine": True,
                 **({"valueFormatter": formato} if formato else {})},
        grid={"left": 8, "right": 28, "top": 8, "bottom": 8, "containLabel": True},
        yAxis=eje_categorias(list(etiquetas), inverse=True,
                             axisLabel={"color": TINTA_SUAVE, "width": 190, "overflow": "truncate"}),
        xAxis=eje_valores(formato),
        series=[barras(nombre, list(valores), color or SERIES[0], barMaxWidth=22,
                       itemStyle={"borderRadius": [0, 4, 4, 0], "color": color or SERIES[0]},
                       label={"show": len(valores) <= 15, "position": "right", "color": TINTA_SUAVE,
                              "formatter": "lbl:pct" if formato == "fmt:pct" else "lbl:num"})],
    )


def columnas(etiquetas, series, formato=None, apiladas=False, rotar=None, colores=None):
    """Barras verticales. series = {"nombre": [valores], ...}."""
    etiquetas = list(etiquetas)
    rot = rotar if rotar is not None else (30 if len(etiquetas) > 7 else 0)
    return base(
        tooltip={"trigger": "axis", "axisPointer": {"type": "shadow"}, "confine": True,
                 **({"valueFormatter": formato} if formato else {})},
        legend=leyenda() if len(series) > 1 else {"show": False},
        grid={"left": 28 if rot else 8, "right": 16, "top": 36 if len(series) > 1 else 16, "bottom": 8,
              "containLabel": True},
        xAxis=eje_categorias(etiquetas, axisLabel={"color": TINTA_SUAVE, "interval": 0, "rotate": rot,
                                                   "width": 110, "overflow": "truncate"}),
        yAxis=eje_valores(formato),
        series=[barras(n, list(v), (colores or SERIES)[i % len(colores or SERIES)],
                       **({"stack": "total"} if apiladas else {}))
                for i, (n, v) in enumerate(series.items())],
    )


def lineas(etiquetas, series, formato=None, area=False):
    """Una o más líneas sobre el mismo eje. series = {"nombre": [valores], ...}."""
    etiquetas = list(etiquetas)
    return base(
        tooltip={"trigger": "axis", "confine": True, **({"valueFormatter": formato} if formato else {})},
        legend=leyenda() if len(series) > 1 else {"show": False},
        grid={"left": 8, "right": 16, "top": 36 if len(series) > 1 else 16, "bottom": 8, "containLabel": True},
        xAxis=eje_categorias(etiquetas, boundaryGap=False),
        yAxis=eje_valores(formato),
        series=[linea(n, list(v), SERIES[i % len(SERIES)],
                      **({"areaStyle": {"opacity": .12}} if area else {}))
                for i, (n, v) in enumerate(series.items())],
        dataZoom=[{"type": "inside"}] if len(etiquetas) > 36 else [],
    )


def torta(pares, formato=None, colores=None):
    """Anillo. pares = [(etiqueta, valor), ...]. Usar solo con pocas categorías."""
    datos = [{"name": str(e), "value": v} for e, v in pares]
    if colores:
        for d, c in zip(datos, colores):
            d["itemStyle"] = {"color": c}
    return base(
        tooltip={"trigger": "item", "confine": True},
        legend=leyenda(type="scroll"),
        series=[{"type": "pie", "radius": ["45%", "72%"], "center": ["50%", "56%"],
                 "itemStyle": {"borderColor": "#fff", "borderWidth": 2},
                 "label": {"formatter": "{b}\n{d}%", "color": TINTA_SUAVE},
                 "data": datos}],
    )


def embudo(pares):
    """Embudo de etapas. pares = [(etapa, valor), ...] en orden."""
    return base(
        tooltip={"trigger": "item", "confine": True},
        series=[{"type": "funnel", "left": "10%", "width": "80%", "top": 10, "bottom": 10,
                 "sort": "none", "gap": 3, "minSize": "18%",
                 "label": {"show": True, "position": "inside", "formatter": "{b}\n{c}", "color": "#fff",
                           "fontWeight": 600},
                 "itemStyle": {"borderColor": "#fff", "borderWidth": 1},
                 "data": [{"name": str(e), "value": v, "itemStyle": {"color": AZUL[min(len(AZUL) - 1, 6 - i)]}}
                          for i, (e, v) in enumerate(pares)]}],
    )


def dispersion(puntos, nombre_x, nombre_y, formato_x=None, formato_y=None):
    """puntos = [(x, y, etiqueta), ...]"""
    return base(
        tooltip={"trigger": "item", "confine": True, "formatter": "{b}"},
        grid={"left": 8, "right": 24, "top": 30, "bottom": 30, "containLabel": True},
        xAxis=eje_valores(formato_x, name=nombre_x, nameLocation="middle", nameGap=28),
        yAxis=eje_valores(formato_y, name=nombre_y),
        series=[{"type": "scatter", "symbolSize": 12, "itemStyle": {"color": SERIES[0], "opacity": .75},
                 "data": [{"name": str(e), "value": [x, y]} for x, y, e in puntos]}],
    )


def mapa_calor(x, y, valores, formato=None):
    """valores = [[ix, iy, v], ...]"""
    maximo = max((v for _, _, v in valores), default=1) or 1
    return base(
        tooltip={"trigger": "item", "confine": True},
        grid={"left": 8, "right": 16, "top": 8, "bottom": 50, "containLabel": True},
        xAxis=eje_categorias(list(x), splitArea={"show": True}),
        yAxis=eje_categorias(list(y), splitArea={"show": True}),
        visualMap={"min": 0, "max": maximo, "calculable": True, "orient": "horizontal", "left": "center",
                   "bottom": 0, "inRange": {"color": AZUL}, "itemHeight": 120},
        series=[{"type": "heatmap", "data": valores, "label": {"show": len(valores) <= 120},
                 "emphasis": {"itemStyle": {"shadowBlur": 6}}}],
    )
