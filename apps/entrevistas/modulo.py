"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "entrevistas",
    "titulo": "Entrevistas",
    "descripcion": "Resumen, psicólogos, calidad, candidatos, canales, pedidos y análisis cualitativo y psicológico de las entrevistas.",
    "icono": "bi-chat-square-text",
    "color": "#0E7C86",
    "palabras_clave": "psicologos puntajes calidad canales publicacion candidatos cualitativo psicologico motivacion",
}


def resumen():
    return services.resumen_landing()
