"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "viaticos",
    "titulo": "Viáticos",
    "descripcion": "Gasto en viáticos por cliente, candidato y mes, observaciones y anomalías.",
    "icono": "bi-fuel-pump",
    "color": "#B4561B",
    "palabras_clave": "viaticos gastos combustible peajes anomalias duplicados observaciones",
    # Preguntale a Rafa: preguntas sugeridas y tablas en las que se enfoca
    "preguntas": [
        "¿Cuánto se gastó en viáticos por mes este año?",
        "Top 10 clientes por monto de viáticos este año",
        "¿Cuál es el viático promedio por asignación, por cliente?",
        "¿Cuáles fueron los 20 viáticos más altos del último mes?",
        "¿Cómo se comparan los viáticos de este año con los del año pasado, mes a mes?",
    ],
    "tablas": ["HistorialViaticos", "Asignaciones", "Pedidos", "Clientes"],
}


def resumen():
    return services.resumen_landing()
