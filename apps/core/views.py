from django.http import Http404
from django.shortcuts import render

from .analisis import PRIORIDADES, TIPOS
from .registry import obtener_catalogo, obtener_modulo, obtener_modulos
from .utils import PERIODOS, leer_periodo


def landing(request):
    contexto = {
        "modulos": obtener_modulos(con_resumen=True),
        "usuario_nombre": "Eduardo",  # fijo hasta tener login
    }
    return render(request, "core/landing.html", contexto)


def _modulo_y_catalogo(slug):
    modulo = obtener_modulo(slug)
    catalogo = obtener_catalogo(slug)
    if modulo is None or catalogo is None:
        raise Http404("Módulo inexistente")
    return modulo, catalogo


def modulo(request, modulo):
    """Portada del módulo: los análisis disponibles agrupados por tipo."""
    mod, catalogo = _modulo_y_catalogo(modulo)
    return render(request, "core/modulo.html", {
        "modulo": mod,
        "grupos": catalogo.por_tipo(),
    })


def analisis(request, modulo, analisis):
    mod, catalogo = _modulo_y_catalogo(modulo)
    item = catalogo.obtener(analisis)
    if item is None:
        raise Http404("Análisis inexistente")

    periodo = leer_periodo(request)
    datos = item["funcion"](periodo)
    for accion in datos.get("acciones", []):
        accion["prioridad_info"] = PRIORIDADES[accion["prioridad"]]

    return render(request, "core/analisis.html", {
        "modulo": mod,
        "grupos": catalogo.por_tipo(),
        "item": item,
        "tipo": TIPOS[item["tipo"]],
        "periodo": periodo,
        "periodos": PERIODOS,
        "datos": datos,
    })
