"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "entrevistas",
    "titulo": "Entrevistas",
    "descripcion": "Resumen, psicólogos, calidad, candidatos, canales, pedidos y análisis cualitativo y psicológico de las entrevistas.",
    "icono": "bi-chat-square-text",
    "color": "#0E7C86",
    "palabras_clave": "psicologos puntajes calidad canales publicacion candidatos cualitativo psicologico motivacion",
    # Preguntale a Rafa: preguntas sugeridas y tablas en las que se enfoca
    "preguntas": [
        "¿Cuántas entrevistas hizo cada psicólogo este mes?",
        "¿Cuántas entrevistas hubo por mes en el último año?",
        "¿Por qué canal de publicación llegan más candidatos entrevistados?",
        "¿Qué porcentaje de los entrevistados este año terminó asignado?",
        "¿Para qué clientes se hicieron más entrevistas este año?",
    ],
    "tablas": ["Entrevistas", "Psicologos", "CanalesPublicacionAvisos", "Pedidos", "Clientes", "Candidatos", "Asignaciones", "SituacionesLaborales"],
}


def resumen():
    return services.resumen_landing()
