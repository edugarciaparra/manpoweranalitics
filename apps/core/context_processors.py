from django.conf import settings

from .db import sgo_configurada
from .registry import obtener_modulos


def modulos(request):
    """Deja la lista de módulos y el estado de la conexión disponibles en todos los templates."""
    conectada = sgo_configurada()
    sgo = settings.DATABASES.get("sgo", {})
    return {
        "menu_modulos": obtener_modulos(),
        "base_conectada": conectada,
        "base_nombre": f"{sgo.get('HOST', '')} / {sgo.get('NAME', '')}" if sgo else "",
        "ia_configurada": bool(settings.IA_PROVEEDOR),
    }
