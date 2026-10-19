"""Metadatos del módulo para la landing y el menú."""
from . import services

MODULO = {
    "slug": "pedidos",
    "titulo": "Pedidos",
    "descripcion": "Resumen, SLA, demanda, clientes, reclutamiento, embudo, eficiencia y dimensiones de los pedidos.",
    "icono": "bi-clipboard-check",
    "color": "#0B5CAB",
    "palabras_clave": "vacantes sla cumplimiento demanda embudo zombie reclutamiento marcas divisiones",
    # Preguntale a Rafa: preguntas sugeridas y tablas en las que se enfoca
    "preguntas": [
        "¿Cuántos pedidos ingresaron por mes en el último año?",
        "¿Qué clientes hicieron más pedidos este año?",
        "¿Qué porcentaje de pedidos se entregó a tiempo por división este año?",
        "¿Cuántos pedidos están abiertos hoy, por cliente?",
        "¿Cuántas vacantes se pidieron por perfil este año?",
        "¿Cuántos días tarda en promedio el cierre de un pedido, por división?",
    ],
    "tablas": ["Pedidos", "Clientes", "Divisiones", "EstadosPedido", "TiposPedido", "PerfilesCandidatos", "Asignaciones", "PedidosPostulante"],
}


def resumen():
    """Dos indicadores cortos para la tarjeta de la landing."""
    return services.resumen_landing()
