"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "candidatos",
    "titulo": "Candidatos y entrevistas",
    "descripcion": "Postulaciones, entrevistas e ingresos: dónde se frena el proceso de selección.",
    "icono": "bi-person-badge",
    "color": "#C2571A",
    "palabras_clave": "postulantes entrevistas seleccion ingresos embudo",
}


def resumen():
    return services.resumen_landing()
