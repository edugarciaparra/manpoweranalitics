import logging

from django.db import DatabaseError
from django.http import Http404, JsonResponse
from django.shortcuts import render

from .db import BaseNoDisponible

from .filtros import activos, leer_filtros, para_plantilla
from .registry import obtener_catalogo, obtener_modulo, obtener_modulos
from .utils import PERIODO_DEFECTO, PERIODOS

log = logging.getLogger(__name__)
ERRORES_BASE = (BaseNoDisponible, DatabaseError)


def _mensaje_error(e):
    if isinstance(e, BaseNoDisponible):
        return str(e)
    return f"La base de Manpower no respondió: {str(e)[:400]}"


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


def rafa(request, modulo):
    """Preguntale a Rafa: preguntas libres sobre el módulo, con sugerencias propias."""
    mod, catalogo = _modulo_y_catalogo(modulo)
    return render(request, "core/rafa.html", {
        "modulo": mod, "analisis": list(catalogo), "en_rafa": True,
        "modulo_rafa": mod["slug"], "sugerencias": mod.get("preguntas", []),
        "titulo_sugerencias": "Preguntas sugeridas", "pregunta_inicial": request.GET.get("q", "")[:500],
    })


def analisis(request, modulo, analisis):
    mod, catalogo = _modulo_y_catalogo(modulo)
    item = catalogo.obtener(analisis)
    if item is None:
        raise Http404("Análisis inexistente")

    periodos, periodo = _periodo(request, item)
    filtros = leer_filtros(item["filtros"], request.GET)
    try:
        datos = item["funcion"](periodo, filtros) if item["filtros"] else item["funcion"](periodo)
    except ERRORES_BASE as e:
        log.exception("Error de base en %s/%s", modulo, analisis)
        return render(request, "core/error_base.html", {
            "modulo": mod, "analisis": list(catalogo), "item": item, "mensaje": _mensaje_error(e),
        }, status=503)
    datos["conclusiones"] = [c for c in datos.get("conclusiones", []) if c]

    return render(request, "core/analisis.html", {
        "modulo": mod,
        "analisis": list(catalogo),
        "item": item,
        "periodo": periodo,
        "periodos": periodos,
        "datos": datos,
        "graficos": [s["grafico"] for s in datos["secciones"]],
        "filtros": para_plantilla(item["filtros"], filtros),
        "filtros_activos": activos(item["filtros"], filtros),
    })


MAX_FILAS_DETALLE = 2000


def _celda(v):
    """Texto de una celda del modal: números con formato uruguayo y fechas dd/mm/aaaa."""
    from datetime import date, datetime
    from decimal import Decimal
    if v is None:
        return ""
    if isinstance(v, bool):
        return "Sí" if v else "No"
    if isinstance(v, (int, float, Decimal)):
        f = float(v)
        texto = f"{f:,.0f}" if f.is_integer() else f"{f:,.2f}"
        return texto.replace(",", "X").replace(".", ",").replace("X", ".")
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y %H:%M") if (v.hour or v.minute) else v.strftime("%d/%m/%Y")
    if isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    return str(v).strip()


def detalle(request, modulo, analisis):
    """GET /<modulo>/<analisis>/detalle/?clave=...&valor=...&serie=...&periodo=...

    Devuelve en JSON los registros detrás del elemento del gráfico que se cliqueó.
    """
    _, catalogo = _modulo_y_catalogo(modulo)
    item = catalogo.obtener(analisis)
    funcion = catalogo.obtener_detalle(analisis)
    if item is None or funcion is None:
        return JsonResponse({"error": "Este análisis no tiene detalle de registros."}, status=404)

    argumentos = [request.GET.get("clave", ""), request.GET.get("valor", ""),
                  request.GET.get("serie", ""), _periodo(request, item)[1]]
    try:
        if item["filtros"]:
            resultado = funcion(*argumentos, filtros=leer_filtros(item["filtros"], request.GET))
        else:
            resultado = funcion(*argumentos)
    except ERRORES_BASE as e:
        log.exception("Error de base en el detalle de %s/%s", modulo, analisis)
        return JsonResponse({"error": _mensaje_error(e)}, status=503)
    filas = resultado.get("filas", [])
    resultado["total"] = len(filas)
    resultado["filas"] = [[_celda(v) for v in f] for f in filas[:MAX_FILAS_DETALLE]]
    resultado["recortado"] = len(filas) > MAX_FILAS_DETALLE
    return JsonResponse(resultado)
