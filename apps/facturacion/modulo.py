"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "facturacion",
    "titulo": "Facturación",
    "descripcion": "Revenue, clientes, evolución temporal, responsables, portafolio de servicios y segmentación RFM.",
    "icono": "bi-receipt",
    "color": "#0E8A5F",
    "palabras_clave": "ordenes montos factura ingresos revenue rfm pareto responsables servicios",
}


def resumen():
    return services.resumen_landing()
