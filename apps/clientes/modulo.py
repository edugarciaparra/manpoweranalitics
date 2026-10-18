"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "clientes",
    "titulo": "Clientes",
    "descripcion": "Cartera activa, ranking, sectores y clientes que dejaron de pedir.",
    "icono": "bi-buildings",
    "color": "#7A4FD1",
    "palabras_clave": "cartera ranking sector actividad tendencia empresas",
}


def resumen():
    return services.resumen_landing()
