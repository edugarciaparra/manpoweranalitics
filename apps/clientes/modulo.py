"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "clientes",
    "titulo": "Clientes",
    "descripcion": "Cartera, concentración, penetración, actividad y clientes que pueden dejar de pedir.",
    "icono": "bi-buildings",
    "color": "#6A3FD6",
    "palabras_clave": "cartera sector actividad tendencia empresas ejecutivos penetracion",
}


def resumen():
    return services.resumen_landing()
