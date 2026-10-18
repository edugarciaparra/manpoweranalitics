"""
Datos del CV de los candidatos web: experiencia, formación e idiomas.

Con la base conectada cada función lee su consulta: las descripciones (motivo de
baja, curso, nivel educativo, idioma) salen de las tablas de referencia con JOIN.
Sin conexión se generan datos de ejemplo que, igual que las tablas reales,
guardan los Id y buscan la descripción en apps/core/catalogos.py.

Tablas:
    [CVExperiencia]  -> [CausalesBaja]
    [CVFormacion]    -> [CursosCarreras] -> [NivelesEducativos]
    [CVIdiomas]      -> [Competencias]
"""
import random
from datetime import date, timedelta

from apps.core.cache import cache_temporal
from apps.core.catalogos import catalogo, cursos
from apps.core.db import consultar, sgo_configurada

from .services import candidatos_web

# Códigos reales (consulta del 18/10/2026)
TRABAJO_ACTUAL_SI = "S"          # CVExpTrabajoActual: S / N
FORMACION_COMPLETA_SI = "C"      # CVFormCompleto: C = completo, I = incompleto
# CVIdiomaNivel va de 1 a 5. No hay tabla con la descripción de cada nivel:
# se muestra el número. 1 es el más bajo y 5 el más alto.
NIVELES_IDIOMA = {n: f"Nivel {n}" for n in range(1, 6)}
NIVEL_IDIOMA_BUENO = 3           # desde qué nivel se considera "bueno"
NIVEL_IDIOMA_ALTO = 5            # nivel más alto, para puestos bilingües

CONSULTA_EXPERIENCIA = """
SELECT e.[WebUserId], e.[CVExpId], e.[CVExpEmpresa], e.[CVExpCargo], e.[CVExpFechaIngreso],
       e.[CVExpFechaEgreso], e.[CVExpTrabajoActual], cb.[CausalBajaDescripcion]
FROM [CVExperiencia] e
LEFT JOIN [CausalesBaja] cb ON cb.[CausalBajaId] = e.[CausalBajaId]
"""
CONSULTA_FORMACION = """
SELECT f.[WebUserId], f.[CVFormId], cc.[CursoNombre], ne.[NivelEducativoId], ne.[NivelEducativoDescripcion],
       f.[CVFormCompleto], f.[CVFormInstitucion], f.[CVFormFechaInicio], f.[CVFormFechaFin]
FROM [CVFormacion] f
JOIN [CursosCarreras] cc ON cc.[CursoId] = f.[CursoId]
JOIN [NivelesEducativos] ne ON ne.[NivelEducativoId] = cc.[NivelEducativoId]
"""
CONSULTA_IDIOMAS = """
SELECT i.[WebUserId], c.[CompetenciaNombre], i.[CVIdiomaNivel], i.[CVIdiomaAniosExp]
FROM [CVIdiomas] i
JOIN [Competencias] c ON c.[CompetenciaId] = i.[CVIdiomaId]
"""


def _texto(v):
    return (v or "").strip()


def _fecha(v):
    return v.date() if hasattr(v, "date") else v


def _meses(ingreso, egreso):
    if not ingreso or not egreso:
        return 0
    return max(1, round((egreso - ingreso).days / 30))


# ==========================================================================
# Experiencia
# ==========================================================================
def _experiencia_sgo():
    hoy = date.today()
    filas = []
    for r in consultar(CONSULTA_EXPERIENCIA):
        actual = _texto(r["CVExpTrabajoActual"])
        ingreso = _fecha(r["CVExpFechaIngreso"])
        egreso = hoy if actual == TRABAJO_ACTUAL_SI else _fecha(r["CVExpFechaEgreso"])
        filas.append({
            "web_user_id": int(r["WebUserId"]), "id": int(r["CVExpId"]),
            "empresa": _texto(r["CVExpEmpresa"]), "cargo": _texto(r["CVExpCargo"]).capitalize() or "Sin dato",
            "ingreso": ingreso, "egreso": egreso, "meses": _meses(ingreso, egreso), "actual": actual,
            "causal": None if actual == TRABAJO_ACTUAL_SI else (_texto(r["CausalBajaDescripcion"]) or "Sin motivo"),
        })
    return tuple(filas)


# Cargos y empresas son texto libre en el CV; estos son solo de ejemplo
_CARGOS_EJ = {"Cajero/a": 16, "Repositor/a": 14, "Atención al cliente": 12, "Vendedor/a": 11, "Operario/a": 10,
              "Administrativo/a": 9, "Auxiliar de depósito": 7, "Chofer": 4, "Recepcionista": 4, "Mozo/a": 4,
              "Limpieza": 4, "Seguridad": 3, "Analista": 3, "Encargado/a": 3, "Telemarketer": 5}
_EMPRESAS_EJ = ["Supermercado del Este", "Comercial Norte", "Logística Sur", "Call Center Uno", "Industrias Unidas",
                "Farmacia Central", "Distribuidora Oeste", "Restaurante La Plaza", "Servicios Generales", "Hotel Costa"]


def _experiencia_ejemplo():
    r = random.Random(1311)
    hoy = date.today()
    causales = catalogo("CausalesBaja")
    ids_causal = sorted(causales)
    # Distribución parecida a la real (el Id 9 es el más frecuente, después 8, 5 y 2)
    peso_causal = {9: 35, 8: 18, 5: 17, 2: 6, 1: 2, 3: 1, 4: 1, 6: 1, 7: 1, 12: 1}
    filas = []
    for c in candidatos_web():
        edad_laboral = max(0, c["edad"] - 18)
        pesos = [6, 20, 28, 22, 14, 10] if c["etapa"] >= 2 else [16, 27, 26, 17, 9, 5]
        cantidad = min(r.choices([0, 1, 2, 3, 4, 5], weights=pesos)[0], 1 + edad_laboral // 2)
        fin = hoy
        for i in range(cantidad):
            meses = max(1, int(r.expovariate(1 / 22)))
            es_actual = c["salario_actual"] > 0 and i == 0
            egreso = fin if es_actual else fin - timedelta(days=r.randint(15, 240))
            ingreso = egreso - timedelta(days=meses * 30)
            if ingreso.year < hoy.year - edad_laboral - 1:
                break
            causal_id = None
            if not es_actual and r.random() > .12:  # algunos trabajos terminados no tienen motivo, como en la base
                causal_id = r.choices(ids_causal, weights=[peso_causal.get(x, 1) for x in ids_causal])[0]
            filas.append({
                "web_user_id": c["id"], "id": i + 1, "empresa": r.choice(_EMPRESAS_EJ),
                "cargo": r.choices(list(_CARGOS_EJ), weights=list(_CARGOS_EJ.values()))[0],
                "ingreso": ingreso, "egreso": egreso, "meses": meses,
                "actual": TRABAJO_ACTUAL_SI if es_actual else "N",
                # Descripción por Id desde la tabla de referencia (como el JOIN real)
                "causal": None if es_actual else (causales[causal_id] if causal_id else "Sin motivo"),
            })
            fin = ingreso
    return tuple(filas)


@cache_temporal()
def experiencia():
    """Una fila por trabajo declarado."""
    return _experiencia_sgo() if sgo_configurada() else _experiencia_ejemplo()


# ==========================================================================
# Formación
# ==========================================================================
def _formacion_sgo():
    return tuple({
        "web_user_id": int(r["WebUserId"]), "id": int(r["CVFormId"]),
        "nivel": _texto(r["NivelEducativoDescripcion"]), "nivel_orden": int(r["NivelEducativoId"]),
        "curso": _texto(r["CursoNombre"]), "institucion": _texto(r["CVFormInstitucion"]),
        "completo": _texto(r["CVFormCompleto"]),
        "inicio": _fecha(r["CVFormFechaInicio"]), "fin": _fecha(r["CVFormFechaFin"]),
    } for r in consultar(CONSULTA_FORMACION))


def _formacion_ejemplo():
    r = random.Random(2718)
    hoy = date.today()
    niveles = catalogo("NivelesEducativos")
    ids_nivel = sorted(niveles)
    cursos_por_nivel = {}
    for curso_id, (_, nivel_id) in cursos().items():
        cursos_por_nivel.setdefault(nivel_id, []).append(curso_id)
    filas = []
    for c in candidatos_web():
        pesos = [2, 9, 33, 20, 15, 17, 4] if c["etapa"] >= 2 else [5, 15, 34, 16, 12, 15, 3]
        pos_max = r.choices(range(len(ids_nivel)), weights=pesos[:len(ids_nivel)])[0]
        if c["edad"] < 23:
            pos_max = min(pos_max, 4)
        posiciones = sorted({pos_max} | ({pos_max - 1} if pos_max > 1 and r.random() < .35 else set()))
        for i, pos in enumerate(posiciones):
            nivel_id = ids_nivel[pos]
            opciones = cursos_por_nivel.get(nivel_id)
            if not opciones:
                continue
            curso_id = r.choice(opciones)
            completo = r.random() < (.62 if pos == pos_max else .95)
            inicio = hoy - timedelta(days=r.randint(400, 365 * max(2, c["edad"] - 14)))
            filas.append({
                "web_user_id": c["id"], "id": i + 1,
                "nivel": niveles[nivel_id], "nivel_orden": nivel_id,
                "curso": cursos()[curso_id][0], "institucion": "Institución de ejemplo",
                "completo": FORMACION_COMPLETA_SI if completo else "I",
                "inicio": inicio, "fin": inicio + timedelta(days=365 * r.randint(1, 5)),
            })
    return tuple(filas)


@cache_temporal()
def formacion():
    """Una fila por estudio declarado."""
    return _formacion_sgo() if sgo_configurada() else _formacion_ejemplo()


# ==========================================================================
# Idiomas
# ==========================================================================
def _idiomas_sgo():
    return tuple({
        "web_user_id": int(r["WebUserId"]), "idioma": _texto(r["CompetenciaNombre"]),
        "nivel": int(r["CVIdiomaNivel"]), "anios": int(r["CVIdiomaAniosExp"] or 0),
    } for r in consultar(CONSULTA_IDIOMAS))


def _idiomas_ejemplo():
    r = random.Random(3141)
    idiomas_tabla = catalogo("Idiomas")
    ids = sorted(idiomas_tabla)
    pesos = [max(1, 70 // (i + 1) ** 1.6) for i in range(len(ids))]  # el primero es el más común
    filas = []
    for c in candidatos_web():
        joven = c["edad"] < 30
        cantidad = r.choices([0, 1, 2, 3], weights=[32, 42, 20, 6] if joven else [52, 34, 11, 3])[0]
        elegidos = set()
        while len(elegidos) < min(cantidad, len(ids)):
            elegidos.add(r.choices(ids, weights=pesos)[0])
        for idioma_id in elegidos:
            nivel = r.choices([1, 2, 3, 4, 5], weights=[16, 4, 38, 6, 36] if joven else [28, 6, 38, 5, 23])[0]
            filas.append({"web_user_id": c["id"], "idioma": idiomas_tabla[idioma_id], "nivel": nivel,
                          "anios": max(0, int(r.gauss(nivel * 2, 2)))})
    return tuple(filas)


@cache_temporal()
def idiomas():
    """Una fila por idioma declarado."""
    return _idiomas_sgo() if sgo_configurada() else _idiomas_ejemplo()


# ==========================================================================
# Resumen por candidato
# ==========================================================================
@cache_temporal()
def perfil_cv():
    """{web_user_id: {anios_exp, trabajos, nivel_max, nivel_orden, nivel_completo, curso, idiomas}}."""
    perfil = {c["id"]: {"anios_exp": 0.0, "trabajos": 0, "nivel_max": None, "nivel_orden": -1,
                        "nivel_completo": False, "curso": "", "idiomas": []} for c in candidatos_web()}
    for e in experiencia():
        p = perfil.get(e["web_user_id"])
        if p:
            p["anios_exp"] += e["meses"] / 12
            p["trabajos"] += 1
    for f in formacion():
        p = perfil.get(f["web_user_id"])
        if p and f["nivel_orden"] > p["nivel_orden"]:
            p.update(nivel_max=f["nivel"], nivel_orden=f["nivel_orden"], curso=f["curso"],
                     nivel_completo=f["completo"] == FORMACION_COMPLETA_SI)
    for i in idiomas():
        p = perfil.get(i["web_user_id"])
        if p:
            p["idiomas"].append(f"{i['idioma']} ({NIVELES_IDIOMA.get(i['nivel'], i['nivel'])})".replace("(Nivel", "(nivel"))
    for p in perfil.values():
        p["anios_exp"] = round(p["anios_exp"], 1)
    return perfil
