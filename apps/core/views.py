from django.http import Http404, JsonResponse
from django.shortcuts import render

from .registry import obtener_catalogo, obtener_modulo, obtener_modulos
from .utils import PERIODO_DEFECTO, PERIODOS


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


def _periodo(request, item):
    """Opciones de período del análisis y el período elegido (o el de por defecto)."""
    periodos = item["periodos"] or PERIODOS
    elegido = request.GET.get("periodo")
    if elegido not in periodos:
        elegido = item["periodo_defecto"] or (PERIODO_DEFECTO if item["periodos"] is None else next(iter(periodos)))
    return periodos, elegido


def modulo(request, modulo):
    """Portada del módulo: los análisis disponibles."""
    mod, catalogo = _modulo_y_catalogo(modulo)
    return render(request, "core/modulo.html", {"modulo": mod, "analisis": list(catalogo)})


def analisis(request, modulo, analisis):
    mod, catalogo = _modulo_y_catalogo(modulo)
    item = catalogo.obtener(analisis)
    if item is None:
        raise Http404("Análisis inexistente")

    periodos, periodo = _periodo(request, item)
    datos = item["funcion"](periodo)

    return render(request, "core/analisis.html", {
        "modulo": mod,
        "analisis": list(catalogo),
        "item": item,
        "periodo": periodo,
        "periodos": periodos,
        "datos": datos,
        "graficos": [s["grafico"] for s in datos["secciones"]],
    })


MAX_FILAS_DETALLE = 2000


def detalle(request, modulo, analisis):
    """GET /<modulo>/<analisis>/detalle/?clave=...&valor=...&serie=...&periodo=...

    Devuelve en JSON los registros detrás del elemento del gráfico que se cliqueó.
    """
    _, catalogo = _modulo_y_catalogo(modulo)
    item = catalogo.obtener(analisis)
    funcion = catalogo.obtener_detalle(analisis)
    if item is None or funcion is None:
        return JsonResponse({"error": "Este análisis no tiene detalle de registros."}, status=404)

    resultado = funcion(
        request.GET.get("clave", ""),
        request.GET.get("valor", ""),
        request.GET.get("serie", ""),
        _periodo(request, item)[1],
    )
    filas = resultado.get("filas", [])
    resultado["total"] = len(filas)
    resultado["filas"] = [[str(v) if v is not None else "" for v in f] for f in filas[:MAX_FILAS_DETALLE]]
    resultado["recortado"] = len(filas) > MAX_FILAS_DETALLE
    return JsonResponse(resultado)
