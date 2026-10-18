"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "pedidos",
    "titulo": "Pedidos",
    "descripcion": "Resumen, SLA, demanda, clientes, reclutamiento, embudo, eficiencia y dimensiones de los pedidos.",
    "icono": "bi-clipboard-check",
    "color": "#0B5CAB",
    "palabras_clave": "vacantes sla cumplimiento demanda embudo zombie reclutamiento marcas divisiones",
}


def resumen():
    """Dos indicadores cortos para la tarjeta de la landing."""
    return services.resumen_landing()
