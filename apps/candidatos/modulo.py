"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "candidatos",
    "titulo": "Candidatos",
    "descripcion": "Perfil, disponibilidad, geografía, experiencia, calidad de datos, pruebas, referencias, desempeño en asignaciones y buscador.",
    "icono": "bi-person-badge",
    "color": "#E07A00",
    "palabras_clave": "candidatos perfil disponibilidad libreta zafrales geografico pruebas referencias calidad datos desempeño asignaciones buscar búsqueda",
    # Preguntale a Rafa: preguntas sugeridas y tablas en las que se enfoca
    "preguntas": [
        "¿Cuántos candidatos asignables hay por perfil?",
        "¿Cuántos candidatos tienen libreta de conducir, por categoría?",
        "¿Cuántos candidatos hay por departamento de residencia?",
        "¿Qué pruebas se toman más y qué porcentaje se aprueba?",
        "¿Cuántas referencias chequeadas hay por nivel de seguridad este año?",
        "¿Cuál es el desempeño promedio de las asignaciones por cliente?",
    ],
    "tablas": ["Candidatos", "PerfilesCandidatos", "Departamentos", "Paises", "NivelesEducativos", "CategoriasLibretaConducir", "CandidatoPruebas", "Pruebas", "CandidatoCheckReferencias", "Asignaciones"],
}


def resumen():
    return services.resumen_landing()
