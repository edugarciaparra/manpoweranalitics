"""
Gráfico ECharts para el resultado de una consulta en lenguaje natural.

El modelo sugiere tipo, columna x y columnas y; acá se verifica que existan y
sean numéricas. Si la sugerencia no sirve, se elige un gráfico según la forma
de los datos, o ninguno.
"""
from apps.core import graficos as g

MAX_CATEGORIAS = 40
MAX_SERIES = 4


def _numerica(filas, i):
    valores = [f[i] for f in filas if f[i] is not None]
    return bool(valores) and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in valores)


def _parece_fecha(nombre, filas, i):
    if nombre.lower() in ("mes", "año", "anio", "fecha", "semana", "dia", "día", "periodo", "período"):
        return True
    v = next((f[i] for f in filas if f[i] is not None), None)
    return isinstance(v, str) and len(v) in (7, 10) and v[:4].isdigit() and v[4] == "-"


def armar_grafico(sugerencia, columnas, filas):
    if not filas or len(columnas) < 2 or len(filas) < 2:
        return None
    sugerencia = sugerencia or {}
    tipo = sugerencia.get("tipo")
    if tipo == "ninguno":
        return None

    indice = {c: i for i, c in enumerate(columnas)}
    numericas = [i for i in range(len(columnas)) if _numerica(filas, i)]
    x = indice.get(sugerencia.get("x"))
    if x is None or x in numericas:
        x = next((i for i in range(len(columnas)) if i not in numericas), None)
    if x is None:
        return None
    ys = [indice[c] for c in (sugerencia.get("y") or []) if c in indice and indice[c] in numericas]
    ys = (ys or [i for i in numericas if i != x])[:MAX_SERIES]
    if not ys:
        return None

    filas = filas[:MAX_CATEGORIAS] if not _parece_fecha(columnas[x], filas, x) else filas
    etiquetas = ["Sin dato" if f[x] in (None, "") else str(f[x]) for f in filas]

    if tipo not in ("barras", "barras_h", "lineas", "torta"):
        if _parece_fecha(columnas[x], filas, x):
            tipo = "lineas"
        else:
            tipo = "barras_h" if len(filas) > 8 else "barras"
    if tipo == "torta" and (len(filas) > 6 or len(ys) > 1 or any((f[ys[0]] or 0) < 0 for f in filas)):
        tipo = "barras_h"

    leyenda = g.leyenda() if len(ys) > 1 else {"show": False}

    if tipo == "torta":
        return g.base(
            tooltip={"trigger": "item", "confine": True},
            legend=g.leyenda(type="scroll"),
            series=[{"type": "pie", "name": columnas[ys[0]], "radius": ["45%", "72%"], "center": ["50%", "56%"],
                     "itemStyle": {"borderColor": "#fff", "borderWidth": 2},
                     "label": {"formatter": "{b}: {d}%"},
                     "data": [{"name": e, "value": f[ys[0]]} for e, f in zip(etiquetas, filas)]}],
        )

    if tipo == "lineas":
        return g.base(
            legend=leyenda,
            xAxis=g.eje_categorias(etiquetas, boundaryGap=False),
            yAxis=g.eje_valores(),
            series=[g.linea(columnas[i], [f[i] for f in filas]) for i in ys],
            dataZoom=[{"type": "inside"}] if len(filas) > 36 else [],
        )

    if tipo == "barras_h":
        # El primero arriba: ECharts dibuja de abajo hacia arriba
        return g.base(
            legend=leyenda,
            grid={"left": 8, "right": 24, "top": 30 if len(ys) > 1 else 8, "bottom": 8, "containLabel": True},
            yAxis=g.eje_categorias(etiquetas[::-1], axisLabel={"color": g.TINTA_SUAVE, "width": 180,
                                                                "overflow": "truncate"}),
            xAxis=g.eje_valores(),
            series=[g.barras(columnas[i], [f[i] for f in filas][::-1],
                             itemStyle={"borderRadius": [0, 4, 4, 0]}) for i in ys],
            _alto=max(260, 26 * len(filas) + 60),
        )

    return g.base(
        legend=leyenda,
        xAxis=g.eje_categorias(etiquetas, axisLabel={"color": g.TINTA_SUAVE, "interval": 0,
                                                     "rotate": 30 if len(filas) > 6 else 0}),
        yAxis=g.eje_valores(),
        series=[g.barras(columnas[i], [f[i] for f in filas]) for i in ys],
    )
