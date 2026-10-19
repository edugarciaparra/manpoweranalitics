"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "clientes",
    "titulo": "Clientes",
    "descripcion": "Cartera, concentración, penetración, actividad y clientes que pueden dejar de pedir.",
    "icono": "bi-buildings",
    "color": "#6A3FD6",
    "palabras_clave": "cartera sector actividad tendencia empresas ejecutivos penetracion",
    # Preguntale a Rafa: preguntas sugeridas y tablas en las que se enfoca
    "preguntas": [
        "¿Cuántos clientes activos hay por sector de actividad?",
        "¿Qué clientes activos no hacen pedidos hace más de 6 meses?",
        "¿Cuántos clientes hay en cada estado?",
        "¿Qué ejecutivos tienen más clientes activos?",
        "¿Cuántos clientes operan en cada línea: industrial, administrativa, profesional, promociones y RPO?",
    ],
    "tablas": ["Clientes", "SectoresActividad", "TiposCliente", "EstadosCliente", "Tendencias", "EjecutivosCuenta", "Pedidos"],
}


def resumen():
    return services.resumen_landing()
