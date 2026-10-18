"""
Datos del módulo Candidatos.

Por ahora salen de los procesos de ejemplo (apps/core/datos_ejemplo.py).
Al conectar sgo_new, candidatos() pasa a ser la consulta a [Candidatos]
cruzada con su entrevista y su resultado, sin nombre, documento, teléfono,
email ni dirección.
"""
from apps.core import datos_ejemplo as ej
from apps.core.utils import desde_periodo

NIVELES = ej.NIVELES
CANALES = ej.CANALES


def candidatos(periodo=None):
    filas = list(ej.procesos())
    if periodo is None:
        return filas
    desde = desde_periodo(periodo)
    return [f for f in filas if f["fecha"] >= desde]


def resumen_landing():
    mes = candidatos("30")
    return [
        {"valor": len(mes), "texto": "candidatos en 30 días"},
        {"valor": sum(1 for c in candidatos() if c["en_proceso"]), "texto": "en proceso"},
    ]
