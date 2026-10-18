"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "viaticos",
    "titulo": "Viáticos",
    "descripcion": "Gasto en viáticos por cliente, candidato y mes, observaciones y anomalías.",
    "icono": "bi-fuel-pump",
    "color": "#B4561B",
    "palabras_clave": "viaticos gastos combustible peajes anomalias duplicados observaciones",
}


def resumen():
    return services.resumen_landing()
