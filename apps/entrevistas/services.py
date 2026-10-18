"""
Datos del módulo Entrevistas.

Por ahora salen de los procesos de ejemplo (apps/core/datos_ejemplo.py).
Al conectar sgo_new, entrevistas() pasa a ser la consulta a [Entrevistas]
con [Psicologos] y el resultado del candidato en el pedido.
"""
from apps.core import datos_ejemplo as ej
from apps.core.utils import desde_periodo

ETAPAS = ej.ETAPAS
PSICOLOGOS = ej.PSICOLOGOS
PUESTOS = ej.PUESTOS


def entrevistas(periodo=None):
    filas = list(ej.procesos())
    if periodo is None:
        return filas
    desde = desde_periodo(periodo)
    return [f for f in filas if f["fecha"] >= desde]


def resumen_landing():
    mes = entrevistas("30")
    return [
        {"valor": len(mes), "texto": "entrevistas en 30 días"},
        {"valor": sum(1 for e in mes if e["etapa"] == 2), "texto": "ingresos"},
    ]
