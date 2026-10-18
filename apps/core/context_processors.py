from .registry import obtener_modulos


def modulos(request):
    """Deja la lista de módulos disponible en todos los templates (menú)."""
    return {"menu_modulos": obtener_modulos()}
