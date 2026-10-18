import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.core.registry import obtener_catalogo
from apps.core.utils import PERIODO_DEFECTO

from .proveedores import get_proveedor


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
