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
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]

# Rampas secuenciales de un solo tono, de claro a oscuro
AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
NARANJA = ["#fde3d6", "#f8bfa3", "#f29a72", "#eb6834", "#c9521f", "#a03f17", "#7a2f10"]

# Divergente: positivo / negativo con gris en el medio
POSITIVO, NEGATIVO, NEUTRO = "#2a78d6", "#e34948", "#c3c2b7"

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
        "textStyle": {"fontFamily": "Plus Jakarta Sans, system-ui, sans-serif", "color": TINTA_SUAVE},
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
             "areaStyle": {"color": "rgba(42,120,214,.14)"}, "itemStyle": {"color": "rgba(42,120,214,.35)"},
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
