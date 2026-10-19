"""
Consultas de las pantallas migradas del SGO, siempre contra la base de Manpower.

    filas = sgo.filas(sql, params)      lista de dicts
    fila  = sgo.fila(sql, params)       un dict (o {} si no hay filas)
    valor = sgo.valor(sql, params)      el primer valor de la primera fila

Ejecutan el SQL tal cual, con parámetros %s. Si la base no está conectada
levantan BaseNoDisponible y la pantalla muestra el error.
"""
from .db import consultar


def filas(sql, params=None):
    return consultar(sql, params or [])


def fila(sql, params=None):
    r = filas(sql, params)
    return r[0] if r else {}


def valor(sql, params=None):
    r = fila(sql, params)
    return next(iter(r.values())) if r else None


def num(v, defecto=0):
    """Número (float o int) a partir de lo que devuelve la base (Decimal, None, ...)."""
    if v is None:
        return defecto
    try:
        f = float(v)
    except (TypeError, ValueError):
        return defecto
    return int(f) if f.is_integer() else f


def en_lista(nombre_columna, valores):
    """('col IN (%s, %s)', [v1, v2]) para filtros de varios valores."""
    marcas = ", ".join(["%s"] * len(valores))
    return f"{nombre_columna} IN ({marcas})", list(valores)
