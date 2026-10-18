import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.core.db import sgo_configurada

from apps.core.registry import obtener_catalogo
from apps.core.utils import PERIODO_DEFECTO

from .consulta import ErrorConsulta, responder_pregunta
from .models import ConsultaIA
from .proveedores import get_proveedor

log = logging.getLogger(__name__)

SUGERENCIAS = [
    "¿Cuántos clientes activos hay por sector?",
    "Top 10 clientes por facturación de los últimos 12 meses",
    "¿Cómo evolucionaron los pedidos por mes en el último año?",
    "¿Qué porcentaje de pedidos se entregó a tiempo por división este año?",
    "Candidatos web por departamento",
    "¿Cuántas entrevistas hizo cada psicólogo este mes?",
    "Asignaciones vigentes por cliente, top 15",
    "Motivos de baja más frecuentes en el último año",
]


def consultar_pagina(request):
    """Pantalla para preguntar a la base en lenguaje natural."""
    return render(request, "ia/consultar.html", {
        "sugerencias": SUGERENCIAS,
        "pregunta_inicial": request.GET.get("q", "")[:500],
        "modo_demo": settings.IA_PROVEEDOR == "mock",
        "base_conectada": sgo_configurada(),
    })


def _registrar(request, pregunta, resultado=None, error="", proveedor=""):
    try:
        ConsultaIA.objects.create(
            usuario=request.user.get_username() if request.user.is_authenticated else "",
            pregunta=pregunta, error=error, proveedor=proveedor,
            sql=(resultado or {}).get("sql", ""),
            tipo=(resultado or {}).get("tipo", "error"),
            filas=len((resultado or {}).get("filas") or []),
            segundos=(resultado or {}).get("segundos", 0),
        )
    except Exception:  # noqa: BLE001  (la tabla puede no existir si falta migrate)
        log.warning("No se pudo registrar la consulta de IA", exc_info=True)


@require_POST
def consultar(request):
    """POST /ia/consultar/  {"pregunta": "...", "historial": [{"pregunta": "...", "sql": "..."}]}"""
    try:
        cuerpo = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "El cuerpo tiene que ser JSON."}, status=400)

    pregunta = (cuerpo.get("pregunta") or "").strip()[:1000]
    if not pregunta:
        return JsonResponse({"error": "Escribí una pregunta."}, status=400)
    historial = cuerpo.get("historial") if isinstance(cuerpo.get("historial"), list) else []

    try:
        resultado = responder_pregunta(pregunta, historial)
    except ErrorConsulta as e:
        _registrar(request, pregunta, error=str(e), proveedor=settings.IA_PROVEEDOR)
        return JsonResponse({"error": str(e)}, status=422)
    except Exception as e:  # noqa: BLE001
        log.exception("Error en la consulta de IA")
        _registrar(request, pregunta, error=str(e), proveedor=settings.IA_PROVEEDOR)
        return JsonResponse({"error": f"No se pudo responder: {e}"}, status=502)

    _registrar(request, pregunta, resultado, proveedor=settings.IA_PROVEEDOR)
    return JsonResponse(resultado)


@require_POST
def preguntar(request):
    """POST /ia/preguntar/
    {"modulo": "pedidos", "analisis": "evolucion", "periodo": "90", "pregunta": "..."}
    """
    try:
        cuerpo = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "El cuerpo tiene que ser JSON."}, status=400)

    pregunta = (cuerpo.get("pregunta") or "").strip()
    if not pregunta:
        return JsonResponse({"error": "Escribí una pregunta."}, status=400)

    catalogo = obtener_catalogo(cuerpo.get("modulo", ""))
    item = catalogo.obtener(cuerpo.get("analisis", "")) if catalogo else None
    if item is None:
        return JsonResponse({"error": "Análisis desconocido."}, status=404)

    datos = item["funcion"](cuerpo.get("periodo", PERIODO_DEFECTO))
    sistema = (
        "Sos un asistente de análisis para Manpower Uruguay. Respondé en español "
        "rioplatense, breve y con números concretos. El usuario está viendo el análisis "
        f"«{item['titulo']}». Usá solo estos datos:\n"
        f"{json.dumps(datos.get('contexto_ia', {}), ensure_ascii=False, default=str)}\n"
        f"Conclusiones del análisis: {' '.join(datos.get('conclusiones', []))}"
    )

    try:
        proveedor = get_proveedor()
        respuesta = proveedor.responder(sistema, pregunta)
    except Exception as e:  # noqa: BLE001
        return JsonResponse({"error": f"El asistente no pudo responder: {e}"}, status=502)

    return JsonResponse({"respuesta": respuesta, "proveedor": proveedor.nombre})
