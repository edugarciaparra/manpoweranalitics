from django.conf import settings

from .db import sgo_configurada
from .registry import obtener_modulos


def modulos(request):
    """Deja la lista de módulos y el estado de la conexión disponibles en todos los templates."""
    conectada = sgo_configurada()
    return {
        "menu_modulos": obtener_modulos(),
        "base_conectada": conectada,
        "base_nombre": f"{settings.DATABASES['sgo']['HOST']} / {settings.DATABASES['sgo']['NAME']}" if conectada else "",
        "ia_demo": settings.IA_PROVEEDOR == "mock",
    }
