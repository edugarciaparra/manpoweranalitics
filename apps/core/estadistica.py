"""
Cálculos estadísticos simples para los análisis predictivos.

Son modelos livianos (tendencia lineal y estacionalidad mensual) que alcanzan
para proyecciones de corto plazo. Si más adelante hace falta algo más fino,
se reemplaza acá sin tocar los análisis.
"""
import math


def regresion_lineal(valores):
    """Devuelve (pendiente, intercepto) de la recta que mejor ajusta los valores."""
    n = len(valores)
    xs = range(n)
    media_x = (n - 1) / 2
    media_y = sum(valores) / n
    cov = sum((x - media_x) * (y - media_y) for x, y in zip(xs, valores))
    var = sum((x - media_x) ** 2 for x in xs)
    pendiente = cov / var if var else 0
    return pendiente, media_y - pendiente * media_x


def pronostico(valores, pasos=3, estacionalidad=12, confianza=1.28):
    """Proyecta `pasos` períodos hacia adelante.

    Combina la tendencia lineal con un índice estacional por mes (si hay al menos
    dos ciclos completos). La banda usa el desvío de los residuos:
    confianza=1.28 equivale a un intervalo de 80%.

    Devuelve dict con: valores, inferior, superior, pendiente, ajuste.
    """
    n = len(valores)
    pendiente, intercepto = regresion_lineal(valores)
    tendencia = [intercepto + pendiente * i for i in range(n)]

    indices = [1.0] * estacionalidad
    if n >= estacionalidad * 2:
        for m in range(estacionalidad):
            ratios = [valores[i] / tendencia[i] for i in range(m, n, estacionalidad) if tendencia[i]]
            indices[m] = sum(ratios) / len(ratios) if ratios else 1.0

    ajuste = [tendencia[i] * indices[i % estacionalidad] for i in range(n)]
    residuos = [v - a for v, a in zip(valores, ajuste)]
    desvio = math.sqrt(sum(r * r for r in residuos) / max(n - 2, 1))

    futuro, inferior, superior = [], [], []
    for k in range(1, pasos + 1):
        i = n - 1 + k
        v = max((intercepto + pendiente * i) * indices[i % estacionalidad], 0)
        margen = confianza * desvio * math.sqrt(1 + k / n)
        futuro.append(round(v, 1))
        inferior.append(round(max(v - margen, 0), 1))
        superior.append(round(v + margen, 1))

    return {
        "valores": futuro,
        "inferior": inferior,
        "superior": superior,
        "pendiente": pendiente,
        "ajuste": ajuste,
    }


def variacion_pct(actual, anterior):
    if not anterior:
        return 0
    return round((actual - anterior) / anterior * 100, 1)


def mediana(valores):
    v = sorted(valores)
    n = len(v)
    if not n:
        return 0
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2
