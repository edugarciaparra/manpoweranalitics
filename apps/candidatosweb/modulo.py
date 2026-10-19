"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "candidatosweb",
    "titulo": "Candidatos web",
    "descripcion": "Personas registradas en el portal: perfil, ubicación, salarios, disponibilidad y cuántas llegan a ingresar.",
    "icono": "bi-globe2",
    "color": "#E1251B",
    "palabras_clave": "portal web registrados postulantes cv curriculum webusers",
    # Preguntale a Rafa: preguntas sugeridas y tablas en las que se enfoca
    "preguntas": [
        "¿Cuántos candidatos web hay por departamento?",
        "¿Cuántos candidatos web cargaron su CV?",
        "¿Qué idiomas declaran más los candidatos web?",
        "¿Qué nivel educativo tienen los candidatos web según su formación?",
        "¿Cuántos candidatos web actualizaron su registro en el último mes?",
    ],
    "tablas": ["CandidatosWeb", "Departamentos", "Localidades", "EstadosCiviles", "CVExperiencia", "CVFormacion", "CVIdiomas", "Competencias", "CursosCarreras", "NivelesEducativos"],
}


def resumen():
    return services.resumen_landing()
