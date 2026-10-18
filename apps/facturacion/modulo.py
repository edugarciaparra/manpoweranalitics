"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "facturacion",
    "titulo": "Facturación",
    "descripcion": "Órdenes de facturación, montos por mes y clientes que más facturan.",
    "icono": "bi-receipt",
    "color": "#0F8A6B",
    "palabras_clave": "ordenes montos cobro factura ingresos",
}


def resumen():
    return services.resumen_landing()
