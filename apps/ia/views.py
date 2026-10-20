import json
import logging
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.core.db import sgo_configurada

from apps.core.registry import obtener_catalogo, obtener_modulo
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


MAX_FILAS_GUARDADAS = 2000   # filas de cada respuesta que se guardan para volver a mostrarla
PREGUNTAS_EN_HISTORIAL = 40


def _sesion(request):
    """Clave de la sesión del navegador (se crea si todavía no existe)."""
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _clave_conversacion(modulo):
    return f"rafa_conversacion_{modulo or 'general'}"


def _conversacion(request, modulo, nueva=False):
    clave = _clave_conversacion(modulo)
    if nueva or not request.session.get(clave):
        request.session[clave] = uuid.uuid4().hex
    return request.session[clave]


def _para_pantalla(c):
    """Lo que el navegador necesita para volver a mostrar una pregunta guardada (nunca el SQL)."""
    try:
        resultado = json.loads(c.resultado) if c.resultado else {}
    except json.JSONDecodeError:
        resultado = {}
    if c.error and not resultado:
        resultado = {"tipo": "error", "error": c.error}
    return {"id": c.id, "pregunta": c.pregunta, "fecha": c.fecha.strftime("%d/%m %H:%M"), **resultado}


def contexto_chat(request, modulo=None):
    """Datos para dibujar la conversación: sugerencias, preguntas anteriores y la conversación en curso."""
    slug = modulo["slug"] if modulo else ""
    sesion = _sesion(request)
    actual = _conversacion(request, slug)
    try:
        anteriores = list(ConsultaIA.objects.filter(sesion=sesion, modulo=slug)[:PREGUNTAS_EN_HISTORIAL])
    except Exception:  # noqa: BLE001  (falta python manage.py migrate)
        log.warning("No se pudo leer el historial de Rafa", exc_info=True)
        anteriores = []
    turnos = [_para_pantalla(c) for c in reversed(anteriores) if c.conversacion == actual]
    return {
        "sugerencias": modulo.get("preguntas", []) if modulo else SUGERENCIAS,
        "historial": [{"id": c.id, "pregunta": c.pregunta, "fecha": c.fecha.strftime("%d/%m %H:%M"),
                       "actual": c.conversacion == actual, "error": bool(c.error)} for c in anteriores],
        "turnos": turnos,
        "modulo_rafa": slug,
        "pregunta_inicial": request.GET.get("q", "")[:500],
        "ia_configurada": bool(settings.IA_PROVEEDOR),
        "base_conectada": sgo_configurada(),
    }


def consultar_pagina(request):
    """Preguntale a Rafa sobre toda la base."""
    return render(request, "ia/consultar.html", contexto_chat(request))


def _registrar(request, pregunta, modulo, conversacion, resultado=None, error=""):
    resultado = resultado or {}
    para_guardar = {k: v for k, v in resultado.items() if k != "sql"}
    if para_guardar.get("filas"):
        para_guardar["filas"] = para_guardar["filas"][:MAX_FILAS_GUARDADAS]
    try:
        return ConsultaIA.objects.create(
            usuario=request.user.get_username() if request.user.is_authenticated else "",
            pregunta=pregunta, error=error, proveedor=settings.IA_PROVEEDOR,
            sql=resultado.get("sql", ""), tipo=resultado.get("tipo", "error"),
            filas=len(resultado.get("filas") or []), segundos=resultado.get("segundos", 0),
            sesion=_sesion(request), modulo=modulo, conversacion=conversacion,
            resultado=json.dumps(para_guardar, ensure_ascii=False, default=str) if para_guardar else "",
        )
    except Exception:  # noqa: BLE001  (la tabla puede no existir si falta migrate)
        log.warning("No se pudo registrar la consulta de IA", exc_info=True)
        return None


def _historial_sql(request, conversacion):
    """Preguntas anteriores de la conversación con su SQL, para entender las repreguntas («¿y por división?»)."""
    try:
        previas = list(ConsultaIA.objects.filter(sesion=_sesion(request), conversacion=conversacion, tipo="resultado")[:4])
    except Exception:  # noqa: BLE001  (falta python manage.py migrate)
        log.warning("No se pudo leer la conversación de Rafa", exc_info=True)
        return []
    return [{"pregunta": c.pregunta, "sql": c.sql} for c in reversed(previas)]


@require_POST
def consultar(request):
    """POST /ia/consultar/  {"pregunta": "...", "modulo": "pedidos" | ""}"""
    try:
        cuerpo = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "El cuerpo tiene que ser JSON."}, status=400)

    pregunta = (cuerpo.get("pregunta") or "").strip()[:1000]
    if not pregunta:
        return JsonResponse({"error": "Escribí una pregunta."}, status=400)
    modulo = obtener_modulo(str(cuerpo.get("modulo") or "")) if cuerpo.get("modulo") else None
    slug = modulo["slug"] if modulo else ""
    conversacion = _conversacion(request, slug)

    try:
        resultado = responder_pregunta(pregunta, _historial_sql(request, conversacion), modulo)
    except ErrorConsulta as e:
        c = _registrar(request, pregunta, slug, conversacion, error=str(e))
        return JsonResponse({"error": str(e), "id": getattr(c, "id", None)}, status=422)
    except Exception as e:  # noqa: BLE001
        log.exception("Error en la consulta de IA")
        c = _registrar(request, pregunta, slug, conversacion, error=str(e))
        return JsonResponse({"error": f"No se pudo responder: {e}", "id": getattr(c, "id", None)}, status=502)

    c = _registrar(request, pregunta, slug, conversacion, resultado)
    respuesta = {k: v for k, v in resultado.items() if k != "sql"}
    respuesta.update({"id": getattr(c, "id", None), "pregunta": pregunta})
    return JsonResponse(respuesta)


@require_POST
def nueva_conversacion(request):
    """POST /ia/nueva/  {"modulo": "..."}: las próximas preguntas no arrastran el contexto de las anteriores."""
    try:
        cuerpo = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        cuerpo = {}
    _conversacion(request, str(cuerpo.get("modulo") or ""), nueva=True)
    return JsonResponse({"ok": True})


def consulta_guardada(request, id_consulta):
    """GET /ia/consulta/<id>/: una pregunta anterior de este navegador, para volver a mostrarla."""
    try:
        c = ConsultaIA.objects.get(id=id_consulta, sesion=_sesion(request))
    except ConsultaIA.DoesNotExist:
        return JsonResponse({"error": "No se encontró esa pregunta."}, status=404)
    except Exception:  # noqa: BLE001  (falta python manage.py migrate)
        return JsonResponse({"error": "Falta actualizar la base del portal: corré python manage.py migrate."}, status=503)
    return JsonResponse(_para_pantalla(c))


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

    periodo = cuerpo.get("periodo", PERIODO_DEFECTO)
    if item["filtros"]:
        from django.http import QueryDict

        from apps.core.filtros import leer_filtros
        consulta = QueryDict(str(cuerpo.get("filtros") or "").lstrip("?"))
        argumentos = (periodo, leer_filtros(item["filtros"], consulta))
    else:
        argumentos = (periodo,)
    try:
        datos = item["funcion"](*argumentos)
    except Exception as e:  # noqa: BLE001
        return JsonResponse({"error": f"No se pudieron leer los datos de la base: {e}"}, status=503)
    sistema = (
        "Sos Rafa, el analista de datos de Manpower Uruguay. Respondé en español "
        "rioplatense, breve y con números concretos. El usuario está viendo el análisis "
        f"«{item['titulo']}». Usá solo estos datos:\n"
        f"{json.dumps(datos.get('contexto_ia', {}), ensure_ascii=False, default=str)}\n"
        f"Conclusiones del análisis: {' '.join(datos.get('conclusiones', []))}"
    )

    try:
        proveedor = get_proveedor()
        respuesta = proveedor.responder(sistema, pregunta)
    except Exception as e:  # noqa: BLE001
        return JsonResponse({"error": f"Rafa no pudo responder: {e}"}, status=502)

    return JsonResponse({"respuesta": respuesta, "proveedor": proveedor.nombre})
