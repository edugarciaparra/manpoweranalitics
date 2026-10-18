"""
Piezas comunes de las pantallas de Entrevistas (migradas del SGO): filtros,
condiciones, listados para el modal y la clasificación de textos de las
pantallas cualitativa y psicológica (mismas palabras clave que el SGO).
"""
import re
from datetime import date

from apps.core import sgo
from apps.core.filtros import Filtro

F_PSICOLOGO = Filtro.uno("psicologo_id", "Psicólogo", "Psicologos")
F_TIPO = Filtro.uno("tipo_entrevista", "Tipo de entrevista", opciones={"individual": "Individual", "grupal": "Grupal"})
F_SITUACION = Filtro.uno("situacion_laboral_id", "Situación laboral", "SituacionesLaborales")
F_CANAL = Filtro.uno("canal_id", "Canal de publicación", "CanalesPublicacionAvisos")
F_PEDIDO = Filtro.uno("tiene_pedido", "Vinculación", opciones={"si": "Con pedido", "no": "Sin pedido"})
F_DESDE = Filtro.fecha("fecha_desde", "Desde")
F_HASTA = Filtro.fecha("fecha_hasta", "Hasta")
# Las pantallas de texto del SGO arrancan en el 1° de enero del año en curso
F_DESDE_ANIO = Filtro.fecha("fecha_desde", "Desde", defecto=lambda: date(date.today().year, 1, 1))

PUNTAJE_F = "CAST(e.EntrevistaPuntajeFormacion AS FLOAT)"
PUNTAJE_E = "CAST(e.EntrevistaPuntajeExperiencia AS FLOAT)"
TOTAL = f"({PUNTAJE_F} + {PUNTAJE_E})"
AVG_F = f"ROUND(AVG(CASE WHEN {PUNTAJE_F} > 0 THEN {PUNTAJE_F} END), 2)"
AVG_E = f"ROUND(AVG(CASE WHEN {PUNTAJE_E} > 0 THEN {PUNTAJE_E} END), 2)"
AVG_T = f"ROUND(AVG(CASE WHEN {TOTAL} > 0 THEN {TOTAL} END), 2)"
PSICOLOGO = "RTRIM(p.PsicologoNombre) + ' ' + RTRIM(p.PsicologoApellido)"
JOIN_PSI = "INNER JOIN dbo.Psicologos p ON e.EntrevistaPsicologoId = p.PsicologoId"
# Contratado: tuvo una asignación con ingreso posterior a la entrevista
JOIN_CONTRATO = "LEFT JOIN dbo.Asignaciones a ON e.CandidatoId = a.CandidatoId AND a.AsignacionFechaIngreso > e.EntrevistaFecha"
CONTRATADOS = "COUNT(DISTINCT CASE WHEN a.AsignacionFechaIngreso > e.EntrevistaFecha THEN e.CandidatoId END)"
PCT_CONTRATO = f"ROUND(CAST({CONTRATADOS} AS FLOAT) / NULLIF(COUNT(DISTINCT e.CandidatoId), 0) * 100, 2)"
# Variante del SGO en canales y pedidos: alguna vez tuvo una asignación
JOIN_ASIGNADO = "LEFT JOIN (SELECT DISTINCT CandidatoId FROM dbo.Asignaciones) contratados ON e.CandidatoId = contratados.CandidatoId"
ASIGNADOS = "COUNT(DISTINCT contratados.CandidatoId)"
PCT_ASIGNADO = f"ROUND(CAST({ASIGNADOS} AS FLOAT) / NULLIF(COUNT(DISTINCT e.CandidatoId), 0) * 100, 2)"


def where(filtros):
    condiciones, params = ["1=1"], []
    for clave, columna in (("psicologo_id", "e.EntrevistaPsicologoId"), ("situacion_laboral_id", "e.SituacionLaboralId"),
                           ("canal_id", "e.EntrevistaCanalPublicacion")):
        if filtros.get(clave) is not None:
            condiciones.append(f"{columna} = %s")
            params.append(filtros[clave])
    if filtros.get("tipo_entrevista") == "individual":
        condiciones.append("e.EntrevistaEsGrupal = 'N'")
    elif filtros.get("tipo_entrevista") == "grupal":
        condiciones.append("e.EntrevistaEsGrupal = 'S'")
    if filtros.get("tiene_pedido") == "si":
        condiciones.append("e.EntrevistaPedidoId IS NOT NULL")
    elif filtros.get("tiene_pedido") == "no":
        condiciones.append("e.EntrevistaPedidoId IS NULL")
    if filtros.get("fecha_desde"):
        condiciones.append("e.EntrevistaFecha >= %s")
        params.append(filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        condiciones.append("e.EntrevistaFecha <= %s")
        params.append(filtros["fecha_hasta"])
    return " AND ".join(condiciones), params


COLUMNAS_ENTREVISTA = ["Entrevista", "Fecha", "Candidato", "Psicólogo", "Formación", "Experiencia", "Total"]


def entrevistas(filtros, condicion="", params=None, extra="", joins="", columnas_extra=(), orden="e.EntrevistaFecha DESC"):
    """Hasta 500 entrevistas con los filtros de la pantalla y una condición más."""
    w, p = where(filtros)
    sql = f"""
        SELECT TOP 500 e.EntrevistaId, CONVERT(VARCHAR(10), e.EntrevistaFecha, 103) AS fecha,
               RTRIM(c.CandidatoNombre) + ' ' + RTRIM(c.CandidatoApellido) AS candidato, {PSICOLOGO} AS psicologo,
               {PUNTAJE_F} AS puntaje_formacion, {PUNTAJE_E} AS puntaje_experiencia, {TOTAL} AS puntaje_total{extra}
        FROM dbo.Entrevistas e
        INNER JOIN dbo.Candidatos c ON e.CandidatoId = c.CandidatoId
        {JOIN_PSI}
        {joins}
        WHERE {w} {f'AND {condicion}' if condicion else ''}
        ORDER BY {orden}"""
    return sgo.filas(sql, p + list(params or [])), COLUMNAS_ENTREVISTA + list(columnas_extra)


def fecha_texto(v):
    if hasattr(v, "strftime"):
        return v.strftime("%d/%m/%Y")
    return str(v or "")


# ---------------------------------------------------------------------------
# Clasificación de textos (mismas reglas y palabras que el SGO)
# ---------------------------------------------------------------------------
_PALABRA = re.compile(r"\b[a-záéíóúñ]+\b")
POSITIVAS = {"excelente", "bueno", "buena", "proactivo", "proactiva", "destacado", "destacada", "capacitado",
             "capacitada", "motivado", "motivada", "competente", "calificado", "potencial", "fuerte", "responsable",
             "comprometido", "eficiente", "profesional", "amplia", "amplio", "sólido", "sólida", "adecuado", "adecuada",
             "apto", "apta", "destacable", "positivo", "positiva", "favorable"}
NEGATIVAS = {"deficiente", "limitado", "limitada", "inseguro", "insegura", "débil", "conflictivo", "conflictiva",
             "desmotivado", "desmotivada", "inconstante", "poco", "escaso", "escasa", "inadecuado", "inadecuada", "falta",
             "carece", "negativo", "negativa", "desfavorable", "bajo", "baja"}


def sentimiento(texto):
    palabras = _PALABRA.findall((texto or "").lower())
    pos = sum(1 for x in palabras if x in POSITIVAS)
    neg = sum(1 for x in palabras if x in NEGATIVAS)
    return "Positivo" if pos > neg else "Negativo" if neg > pos else "Neutral"


PERFILES = {
    "Ventas y atención": ["ventas", "cliente", "comercial", "atención", "público", "vendedor"],
    "Administrativo": ["administración", "administrativa", "facturación", "archivo", "documentación", "secretaria"],
    "Técnico / IT": ["sistemas", "técnico", "soporte", "reparación", "instalación", "informática", "computadora"],
    "Operativo / logística": ["producción", "operario", "almacén", "logística", "depósito", "stock"],
    "Gerencial / supervisión": ["gestión", "supervisión", "coordinación", "equipo", "liderazgo", "gerente", "jefe"],
}


def perfil(texto):
    t = (texto or "").lower()
    puntos = {k: sum(t.count(w) for w in v) for k, v in PERFILES.items()}
    return max(puntos, key=puntos.get) if max(puntos.values()) > 0 else "Sin clasificar"


ALERTAS = {
    "Problemas de actitud": ["conflicto", "problema", "negativo", "desmotivado", "desinterés"],
    "Falta de estabilidad": ["rotación", "cambios", "múltiples", "trabajos", "despido"],
    "Limitaciones técnicas": ["falta", "carece", "limitado", "escaso", "poco", "conocimiento"],
    "Comunicación deficiente": ["dificultad", "comunicación", "expresión", "inseguro", "tímido"],
}


def alertas(texto):
    """Una entrevista puede tener varias alertas (como en el SGO)."""
    t = (texto or "").lower()
    encontradas = [k for k, v in ALERTAS.items() if any(w in t for w in v)]
    return encontradas or ["Sin alertas"]


TECNICAS = {"excel", "word", "powerpoint", "office", "sistemas", "informática", "contabilidad", "facturación",
            "inventario", "erp", "software"}
BLANDAS = {"comunicación", "liderazgo", "equipo", "proactivo", "proactiva", "responsable", "compromiso", "organización",
           "planificación", "adaptabilidad", "empatía", "iniciativa"}


def habilidades(texto):
    t = (texto or "").lower()
    tec = sum(1 for h in TECNICAS if h in t)
    bla = sum(1 for h in BLANDAS if h in t)
    if tec == 0 and bla == 0:
        return "Ninguna mencionada"
    if tec > bla * 1.5:
        return "Predominan técnicas"
    if bla > tec * 1.5:
        return "Predominan blandas"
    return "Equilibrado"


HOBBIES = {
    "Deportes": ["fútbol", "deporte", "gimnasio", "correr", "natación", "bicicleta", "ejercicio", "running"],
    "Arte y cultura": ["leer", "lectura", "música", "pintura", "cine", "teatro", "arte", "dibujo"],
    "Social": ["amigos", "familia", "salir", "compartir", "reuniones", "social"],
    "Tecnología": ["computadora", "videojuegos", "tecnología", "programar", "internet"],
    "Aire libre": ["pasear", "caminar", "naturaleza", "viajar", "playa", "monte"],
}


def hobby(texto):
    t = (texto or "").lower()
    return next((k for k, v in HOBBIES.items() if any(w in t for w in v)), "Otros")


def grupo_familiar(texto):
    t = (texto or "").lower()
    if "solo" in t or "sola" in t:
        return "Vive solo"
    if "hijos" in t or "hijo" in t or "hija" in t:
        return "Con hijos"
    if any(w in t for w in ("esposa", "esposo", "pareja", "convive")):
        return "Con pareja"
    if any(w in t for w in ("padres", "madre", "padre")):
        return "Con padres"
    if any(n in t for n in ("cinco", "seis", "siete", "5", "6", "7")):
        return "Familia numerosa"
    return "Vive solo"


def impedimento(texto):
    t = (texto or "").lower().strip()
    if not t or t in ("no", "ninguno", "ninguna", "sin impedimentos", "n/a", "-"):
        return "Sin impedimentos"
    if any(w in t for w in ("visión", "vista", "lentes", "anteojos")):
        return "Problemas de visión"
    if any(w in t for w in ("audición", "oído", "auditivo", "sordera")):
        return "Problemas de audición"
    if any(w in t for w in ("columna", "espalda", "movilidad", "pierna", "brazo")):
        return "Problemas motrices"
    return "Otros impedimentos"


_CLICHES = ["perfeccionista", "perfeccionismo", "impaciente", "impaciencia", "workaholic", "exigente"]


def autoconocimiento(fortalezas, debilidades):
    f, d = (fortalezas or "").strip(), (debilidades or "").strip()
    cliche = any(c in d.lower() for c in _CLICHES) and len(d) < 150
    if len(f) > 100 and len(d) > 100 and not cliche:
        return "Alto autoconocimiento"
    if len(f) > 50 and len(d) > 50 and not cliche:
        return "Medio"
    if len(f) > 50 and (len(d) < 50 or cliche):
        return "Defensivo"
    return "Bajo"


MOTIVACIONES = {
    "Crecimiento profesional": ["desarrollo", "aprender", "crecer", "oportunidad", "carrera", "profesional", "conocimiento"],
    "Económica": ["salario", "dinero", "económico", "ganar", "sueldo", "ingreso", "remuneración"],
    "Balance vida-trabajo": ["familia", "tiempo", "equilibrio", "calidad de vida", "balance", "flexibilidad", "horario"],
    "Propósito / impacto": ["ayudar", "contribuir", "impacto", "sociedad", "transformar", "aportar", "cambio"],
    "Estabilidad": ["seguridad", "estable", "permanente", "largo plazo", "continuidad"],
    "Reconocimiento": ["valoración", "prestigio", "reconocimiento", "valorado", "respeto"],
}


def motivacion(texto):
    t = (texto or "").lower()
    puntos = {k: sum(1 for w in v if w in t) for k, v in MOTIVACIONES.items()}
    detectados = [k for k, v in puntos.items() if v > 0]
    if not detectados:
        return "No definida"
    if len(detectados) >= 3:
        return "Múltiples motivaciones"
    return max(puntos, key=puntos.get)


LIDERAZGO = {
    "Líder coach": ["mentor", "guía", "enseña", "apoya", "capacita", "desarrolla", "orienta"],
    "Líder directivo": ["claro", "decisivo", "estructura", "organizado", "define", "instrucciones"],
    "Líder participativo": ["escucha", "involucra", "equipo", "consulta", "opinión", "colaborativo"],
    "Líder delegador": ["autonomía", "confianza", "libertad", "independencia", "delega", "empowerment"],
}


def liderazgo(tipo_supervisor, aspectos_jefe):
    t = f"{tipo_supervisor or ''} {aspectos_jefe or ''}".lower()
    puntos = {k: sum(1 for w in v if w in t) for k, v in LIDERAZGO.items()}
    return max(puntos, key=puntos.get) if max(puntos.values()) > 0 else "Sin preferencia clara"


def manejo_estres(texto):
    t = (texto or "").lower()
    if sum(1 for w in ["solución", "resolví", "actué", "organicé", "planifiqué", "comuniqué", "prioricé"] if w in t) >= 2:
        return "Proactivo / resolutivo"
    if any(w in t for w in ["aprendí", "experiencia", "crecimiento", "mejoré", "fortaleció"]):
        return "Resiliente"
    if any(w in t for w in ["normal", "no me afecta", "nunca", "no tuve"]):
        return "Evitativo"
    return "Reactivo"


def motivo_cambio(texto):
    t = (texto or "").lower()
    crec = sum(1 for w in ["más responsabilidad", "retos", "aprendizaje", "desarrollo", "oportunidad", "crecer"] if w in t)
    bal = sum(1 for w in ["horarios", "menos carga", "flexibilidad", "tiempo", "familia", "equilibrio"] if w in t)
    val = sum(1 for w in ["reconocimiento", "mejor ambiente", "valoración", "apreciado", "respeto"] if w in t)
    if any(w in t for w in ["salir", "no aguanto", "toxic", "malo", "horrible", "terrible"]):
        return "Escape / negativo"
    if crec > max(bal, val):
        return "Búsqueda de crecimiento"
    if bal > val:
        return "Búsqueda de balance"
    return "Búsqueda de valoración"


def resumen_landing():
    try:
        f = sgo.fila("""SELECT COUNT(*) AS entrevistas, COUNT(DISTINCT e.EntrevistaPsicologoId) AS psicologos
                        FROM dbo.Entrevistas e WHERE e.EntrevistaFecha >= DATEADD(DAY, -30, GETDATE())""")
    except Exception:  # noqa: BLE001
        return []
    return [{"valor": sgo.num(f.get("entrevistas")), "texto": "entrevistas en 30 días"},
            {"valor": sgo.num(f.get("psicologos")), "texto": "psicólogos activos"}]
