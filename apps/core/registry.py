"""
Registro de módulos de análisis.

Cada app listada en settings.MODULOS_ANALISIS tiene:
  - modulo.py    MODULO (slug, titulo, descripcion, icono, color) y resumen()
  - analisis.py  catalogo con los análisis del módulo, por tipo

La landing y el menú no conocen los módulos de antemano: los descubren acá.
"""
from importlib import import_module

from django.conf import settings
from django.urls import reverse


def _apps():
    return settings.MODULOS_ANALISIS


def obtener_modulos(con_resumen=False):
    modulos = []
    for ruta_app in _apps():
        mod = import_module(f"{ruta_app}.modulo")
        datos = dict(mod.MODULO)
        datos["url"] = reverse("core:modulo", args=[datos["slug"]])
        datos["cantidad_analisis"] = len(list(obtener_catalogo(datos["slug"]) or []))
        if con_resumen:
            datos["resumen"] = mod.resumen()
        modulos.append(datos)
    return modulos


def obtener_modulo(slug):
    for ruta_app in _apps():
        mod = import_module(f"{ruta_app}.modulo")
        if mod.MODULO["slug"] == slug:
            datos = dict(mod.MODULO)
            datos["url"] = reverse("core:modulo", args=[slug])
            return datos
    return None


def obtener_catalogo(slug):
    for ruta_app in _apps():
        if ruta_app.rsplit(".", 1)[-1] == slug:
            return import_module(f"{ruta_app}.analisis").catalogo
    return None
