"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "pedidos",
    "titulo": "Pedidos",
    "descripcion": "Pedidos de personal abiertos, vencidos y cerrados, por cliente y puesto.",
    "icono": "bi-clipboard-check",
    "color": "#0B5CAB",
    "palabras_clave": "vacantes vencidos cierre puesto calificacion",
}


def resumen():
    """Dos indicadores cortos para la tarjeta de la landing."""
    return services.resumen_landing()
