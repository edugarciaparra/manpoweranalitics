from django.conf import settings

from .db import sgo_configurada
from django.urls import reverse

from .registry import obtener_catalogo, obtener_modulos


def _menu():
    """Módulos con sus análisis, para los menús desplegables de la barra superior."""
    salida = []
    for m in obtener_modulos():
        m["url_rafa"] = reverse("core:rafa", args=[m["slug"]])
        m["analisis"] = [{"slug": a["slug"], "titulo": a["titulo"], "icono": a["icono"],
                          "url": reverse("core:analisis", args=[m["slug"], a["slug"]])}
                         for a in (obtener_catalogo(m["slug"]) or [])]
        salida.append(m)
    return salida


def modulos(request):
    """Deja la lista de módulos y el estado de la conexión disponibles en todos los templates."""
    conectada = sgo_configurada()
    sgo = settings.DATABASES.get("sgo", {})
    return {
        "menu_modulos": _menu(),
        "base_conectada": conectada,
        "base_nombre": f"{sgo.get('HOST', '')} / {sgo.get('NAME', '')}" if sgo else "",
        "ia_configurada": bool(settings.IA_PROVEEDOR),
    }
