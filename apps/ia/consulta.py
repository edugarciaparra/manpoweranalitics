"""
Consultas en lenguaje natural sobre sgo_new.

    resultado = responder_pregunta("¿Cuántos pedidos tuvo cada división este año?", historial)

Pasos:
  1. El modelo recibe el esquema permitido, las relaciones y los códigos, y
     devuelve un JSON con la consulta SQL y cómo graficarla.
  2. La consulta se valida (solo lectura, tablas permitidas, sin datos personales).
  3. Se ejecuta en la base con tiempo máximo y tope de filas. Si falla, el modelo
     recibe el error y tiene un intento más para corregirla.
  4. El modelo recibe las primeras filas del resultado y escribe la respuesta.

Al modelo nunca le llegan datos personales: el esquema no los describe y el
validador rechaza las consultas que los piden, así que tampoco aparecen en
los resultados.
"""
import json
import re
import time
from datetime import date, datetime
from decimal import Decimal

from django.db import connections

from apps.core.db import ALIAS, BaseNoDisponible, sgo_configurada

from .conocimiento import CODIGOS, RELACIONES
from .esquema import texto_esquema
from .graficos import armar_grafico
from .proveedores import get_proveedor
from .sql_seguro import ConsultaNoPermitida, validar

MAX_FILAS = 5000          # filas que se traen de la base
FILAS_PARA_MODELO = 60    # filas que ve el modelo para redactar la respuesta
SEGUNDOS_MAXIMOS = 60     # tiempo máximo de cada consulta
TURNOS_HISTORIAL = 4      # preguntas anteriores que se mandan para entender "y por división?"


class ErrorConsulta(Exception):
    pass


def _sistema_sql():
    return f"""Sos Rafa, el analista de datos de Manpower Uruguay (empresa de recursos humanos: pedidos de personal de clientes, candidatos, entrevistas, asignaciones de personal, facturación y viáticos).
Traducís preguntas en español a UNA consulta T-SQL de SQL Server sobre la base sgo_new.

Reglas:
- Solo SELECT (se permite WITH). Nada que modifique datos.
- Usá solo estas tablas y columnas. Si algo no está, no lo inventes.
- Mostrá siempre descripciones y no Ids: hacé JOIN con las tablas de referencia (EstadosPedido, Divisiones, SectoresActividad, etc.).
- Poné alias claros en español con corchetes, por ejemplo AS [Cliente], AS [Pedidos], AS [Mes].
- Series por mes: columna [Mes] con FORMAT(fecha, 'yyyy-MM'), ordenada ascendente.
- Rankings: TOP N con ORDER BY. Nunca más de TOP 1000 filas.
- Fechas relativas con GETDATE(), DATEADD, DATEFROMPARTS. Hoy es {date.today():%Y-%m-%d}. "Este año" = año calendario actual.
- No pidas datos personales de candidatos (nombres, documentos, contactos, direcciones); solo agregados o Ids.
- Porcentajes: CAST(... AS FLOAT) y ROUND(..., 1).

Esquema (tabla(columna tipo, ...)):
{texto_esquema()}

Relaciones:
{RELACIONES.strip()}

Códigos y criterios:
{CODIGOS.strip()}

Respondé SOLO con un JSON, sin texto antes ni después:
{{"sql": "...", "titulo": "título corto del resultado", "explicacion": "qué calcula, en una frase",
  "grafico": {{"tipo": "barras" | "barras_h" | "lineas" | "torta" | "ninguno", "x": "columna de categorías o fechas", "y": ["columnas numéricas"]}}}}
Usá "barras_h" para rankings, "lineas" para series en el tiempo, "torta" solo con 6 categorías o menos que suman un total, "ninguno" para un único número o listados.
Si la pregunta es ambigua o no se puede responder con estas tablas: {{"aclaracion": "pregunta corta al usuario"}}"""


_SISTEMA_RESPUESTA = """Sos Rafa, el analista de datos de Manpower Uruguay. Te paso una pregunta, la consulta que se ejecutó y su resultado.
Respondé en español rioplatense, claro y breve:
- Primero la respuesta directa en una o dos frases, con los números concretos.
- Después, si aportan, hasta 3 hallazgos cortos, cada uno en una línea que empiece con "- ".
Usá solo los datos del resultado; si están recortados, aclaralo. Números con punto de miles (1.234) y coma decimal. No muestres el SQL."""


def _json_de(texto):
    """Primer objeto JSON del texto (el modelo a veces lo envuelve en ```)."""
    m = re.search(r"\{.*\}", texto or "", re.DOTALL)
    if not m:
        raise ErrorConsulta("El modelo no devolvió una consulta.")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ErrorConsulta("El modelo devolvió una respuesta con formato inválido.") from e


def _valor(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M") if (v.hour or v.minute) else v.strftime("%Y-%m-%d")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, (bytes, bytearray)):
        return None
    return v


def ejecutar(sql):
    """(columnas, filas, recortado). Lectura sin bloquear a quienes están escribiendo."""
    conexion = connections[ALIAS]
    conexion.ensure_connection()
    crudo = conexion.connection
    anterior = getattr(crudo, "timeout", 0)
    try:
        crudo.timeout = SEGUNDOS_MAXIMOS
        with conexion.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
            cursor.execute(sql)
            columnas = [c[0] or f"Columna{i + 1}" for i, c in enumerate(cursor.description or [])]
            filas = cursor.fetchmany(MAX_FILAS + 1)
            cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
    finally:
        crudo.timeout = anterior
    recortado = len(filas) > MAX_FILAS
    return columnas, [[_valor(v) for v in f] for f in filas[:MAX_FILAS]], recortado


def _mensajes(pregunta, historial):
    mensajes = []
    for h in (historial or [])[-TURNOS_HISTORIAL:]:
        if h.get("pregunta") and h.get("sql"):
            mensajes.append({"role": "user", "content": str(h["pregunta"])[:500]})
            mensajes.append({"role": "assistant", "content": json.dumps({"sql": str(h["sql"])[:4000]})})
    mensajes.append({"role": "user", "content": pregunta})
    return mensajes


def _enfoque(modulo):
    """Texto que orienta la consulta hacia las tablas del módulo desde el que se pregunta."""
    if not modulo:
        return ""
    return (f"\n\nLa pregunta se hace desde el módulo «{modulo['titulo']}» ({modulo['descripcion']}). "
            f"Tablas principales del módulo: {', '.join(modulo.get('tablas', []))}. "
            "Usá otras tablas permitidas si la pregunta lo necesita.")


def _generar_y_ejecutar(proveedor, pregunta, historial, modulo=None):
    sistema = _sistema_sql() + _enfoque(modulo)
    mensajes = _mensajes(pregunta, historial)
    ultimo_error = None
    for intento in range(2):
        plan = _json_de(proveedor.completar(sistema, mensajes, max_tokens=1500))
        if plan.get("aclaracion"):
            return plan, None
        sql = plan.get("sql", "")
        try:
            sql = validar(sql)
            plan["sql"] = sql
            return plan, ejecutar(sql)
        except (ConsultaNoPermitida, Exception) as e:  # noqa: BLE001
            ultimo_error = e
            if intento == 0:
                mensajes += [
                    {"role": "assistant", "content": json.dumps(plan, ensure_ascii=False)},
                    {"role": "user", "content": f"La consulta falló: {str(e)[:600].rstrip('.')}. Corregila y devolvé el JSON de nuevo."},
                ]
    if isinstance(ultimo_error, ConsultaNoPermitida):
        raise ErrorConsulta(str(ultimo_error))
    raise ErrorConsulta(f"La consulta no se pudo ejecutar: {str(ultimo_error)[:300]}")


def _redactar(proveedor, pregunta, plan, columnas, filas, recortado):
    muestra = filas[:FILAS_PARA_MODELO]
    contenido = (
        f"Pregunta: {pregunta}\n"
        f"Qué calcula: {plan.get('explicacion', '')}\n"
        f"Columnas: {json.dumps(columnas, ensure_ascii=False)}\n"
        f"Filas en total: {len(filas)}{' (recortado al máximo)' if recortado else ''}\n"
        f"Primeras {len(muestra)} filas: {json.dumps(muestra, ensure_ascii=False, default=str)}"
    )
    return proveedor.completar(_SISTEMA_RESPUESTA, [{"role": "user", "content": contenido}], max_tokens=700)


def responder_pregunta(pregunta, historial=None, modulo=None):
    """Devuelve un dict listo para mandar en JSON a la pantalla."""
    inicio = time.monotonic()
    if not sgo_configurada():
        raise BaseNoDisponible("El portal no está conectado a la base de Manpower: completá SGO_DB_HOST en el archivo .env "
                               "y reiniciá el servidor.")
    proveedor = get_proveedor()

    plan, datos = _generar_y_ejecutar(proveedor, pregunta, historial, modulo)
    if plan.get("aclaracion"):
        return {"tipo": "aclaracion", "respuesta": plan["aclaracion"]}

    base = {"titulo": plan.get("titulo", ""), "explicacion": plan.get("explicacion", ""), "sql": plan["sql"]}

    columnas, filas, recortado = datos
    respuesta = _redactar(proveedor, pregunta, plan, columnas, filas, recortado) if filas else \
        "La consulta no devolvió resultados. Probá con otro período o con menos filtros."
    return {
        **base, "tipo": "resultado", "respuesta": respuesta,
        "columnas": columnas, "filas": filas, "recortado": recortado,
        "grafico": armar_grafico(plan.get("grafico"), columnas, filas),
        "segundos": round(time.monotonic() - inicio, 1),
    }
