"""
Datos del módulo Pedidos.

Por ahora todo sale de funciones con datos de ejemplo. Cuando conectemos
sgo_new, se reemplaza el cuerpo de cada función por su consulta y los
análisis (analisis.py) quedan iguales.
"""
from datetime import date

from apps.core.utils import hace, ultimos_meses

ABIERTO, CERRADO, CANCELADO = "Abierto", "Cerrado", "Cancelado"


def pedidos_abiertos():
    """Pedidos abiertos hoy.

    alta: hace cuántos días se creó. tope: días hasta la fecha tope
    (negativo = ya venció). cubiertas: vacantes ya cubiertas.
    """
    # numero, cliente, puesto, alta, tope, vacantes, cubiertas, ranking_cliente
    filas = [
        (10452, "Tienda Inglesa", "Cajero", 12, -3, 6, 2, "A"),
        (10451, "Ta-Ta", "Repositor", 20, 4, 10, 7, "A"),
        (10449, "Conaprole", "Operario de planta", 41, -11, 4, 1, "A"),
        (10447, "Tienda Inglesa", "Repositor", 35, 6, 8, 3, "A"),
        (10444, "Antel", "Call center", 18, 9, 15, 6, "A"),
        (10430, "Tienda Inglesa", "Cajero", 52, -22, 4, 0, "A"),
        (10455, "Disco", "Cajero", 6, 18, 5, 0, "B"),
        (10456, "Farmashop", "Vendedor", 4, 12, 3, 1, "B"),
        (10457, "UTE", "Administrativo", 9, 2, 2, 0, "B"),
        (10458, "Copsa", "Chofer", 15, 1, 3, 1, "B"),
        (10459, "Pronto!", "Repartidor", 3, 25, 6, 0, "C"),
        (10460, "Zonamerica", "Recepcionista", 22, -5, 1, 0, "C"),
    ]
    return [
        {"numero": n, "cliente": c, "puesto": p, "fecha_alta": hace(a),
         "fecha_tope": hace(-t), "dias_a_tope": t, "vacantes": v, "cubiertas": cu,
         "pendientes": v - cu, "ranking": r}
        for n, c, p, a, t, v, cu, r in filas
    ]


def vencidos():
    hoy = date.today()
    return [p for p in pedidos_abiertos() if p["fecha_tope"] < hoy]


def serie_mensual():
    """Altas y cierres por mes, últimos 25 meses (del más viejo al actual, que está en curso)."""
    altas = [36, 38, 41, 47, 52, 49, 44, 40, 43, 50, 58, 61, 55,
             42, 45, 53, 57, 54, 47, 44, 49, 56, 63, 66, 31]
    cierres = [34, 35, 37, 44, 49, 50, 45, 38, 40, 46, 52, 58, 57,
               40, 41, 49, 52, 55, 48, 42, 45, 51, 57, 61, 24]
    vacantes = [a * 3 + (i % 5) for i, a in enumerate(altas)]
    meses = ultimos_meses(25)
    return meses, altas, cierres, vacantes


def cumplimiento_cliente_puesto():
    """Pedidos cerrados en los últimos 12 meses por cliente y puesto:
    (total, vencidos antes de cubrirse)."""
    return {
        ("Tienda Inglesa", "Cajero"): (42, 13),
        ("Tienda Inglesa", "Repositor"): (35, 6),
        ("Ta-Ta", "Cajero"): (28, 5),
        ("Ta-Ta", "Repositor"): (39, 7),
        ("Disco", "Cajero"): (18, 6),
        ("Disco", "Repositor"): (14, 2),
        ("Antel", "Call center"): (31, 3),
        ("Conaprole", "Operario de planta"): (22, 8),
        ("Conaprole", "Chofer"): (9, 4),
        ("UTE", "Administrativo"): (11, 1),
        ("Copsa", "Chofer"): (13, 6),
        ("Farmashop", "Cajero"): (8, 1),
    }


def resumen_landing():
    abiertos = pedidos_abiertos()
    return [
        {"valor": len(abiertos), "texto": "abiertos"},
        {"valor": len(vencidos()), "texto": "vencidos", "alerta": True},
    ]
