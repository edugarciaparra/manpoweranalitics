"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "candidatos",
    "titulo": "Candidatos",
    "descripcion": "Quiénes se postulan, de qué canales vienen y quiénes tienen más chances de ingresar.",
    "icono": "bi-person-badge",
    "color": "#C2571A",
    "palabras_clave": "postulantes perfil canales puntaje probabilidad",
}


def resumen():
    return services.resumen_landing()
