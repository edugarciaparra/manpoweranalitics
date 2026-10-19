"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "facturacion",
    "titulo": "Facturación",
    "descripcion": "Revenue, clientes, evolución temporal, responsables, portafolio de servicios y segmentación RFM.",
    "icono": "bi-receipt",
    "color": "#0E8A5F",
    "palabras_clave": "ordenes montos factura ingresos revenue rfm pareto responsables servicios",
    # Preguntale a Rafa: preguntas sugeridas y tablas en las que se enfoca
    "preguntas": [
        "¿Cuánto se facturó por mes en el último año, separado por moneda?",
        "Top 10 clientes por facturación de los últimos 12 meses",
        "¿Qué servicios facturan más este año?",
        "¿Cómo viene la facturación de este año contra el año pasado, mes a mes?",
        "¿Qué responsables generaron más facturación este año?",
    ],
    "tablas": ["OrdenesFacturacion", "Pedidos", "Clientes", "Servicios", "Monedas", "EjecutivosCuenta"],
}


def resumen():
    return services.resumen_landing()
