"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "candidatos",
    "titulo": "Candidatos",
    "descripcion": "Perfil, disponibilidad, geografía, experiencia, calidad de datos, pruebas y referencias de los candidatos.",
    "icono": "bi-person-badge",
    "color": "#E07A00",
    "palabras_clave": "candidatos perfil disponibilidad libreta zafrales geografico pruebas referencias calidad datos",
}


def resumen():
    return services.resumen_landing()
