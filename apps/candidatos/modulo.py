"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "candidatos",
    "titulo": "Candidatos",
    "descripcion": "Perfil, disponibilidad, geografía, experiencia, calidad de datos, pruebas, referencias, desempeño en asignaciones y buscador.",
    "icono": "bi-person-badge",
    "color": "#E07A00",
    "palabras_clave": "candidatos perfil disponibilidad libreta zafrales geografico pruebas referencias calidad datos desempeño asignaciones buscar búsqueda",
}


def resumen():
    return services.resumen_landing()
