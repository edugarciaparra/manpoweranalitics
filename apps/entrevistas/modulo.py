"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "entrevistas",
    "titulo": "Entrevistas",
    "descripcion": "Embudo de selección, conversión por puesto y desempeño de cada psicólogo.",
    "icono": "bi-chat-square-text",
    "color": "#0E7C86",
    "palabras_clave": "psicologos embudo seleccion conversion presentados ingresos",
}


def resumen():
    return services.resumen_landing()
