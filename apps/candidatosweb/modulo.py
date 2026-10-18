"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "candidatosweb",
    "titulo": "Candidatos web",
    "descripcion": "Personas registradas en el portal: perfil, ubicación, salarios, disponibilidad y cuántas llegan a ingresar.",
    "icono": "bi-globe2",
    "color": "#E1251B",
    "palabras_clave": "portal web registrados postulantes cv curriculum webusers",
}


def resumen():
    return services.resumen_landing()
