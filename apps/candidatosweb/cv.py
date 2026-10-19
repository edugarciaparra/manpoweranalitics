"""
Datos del CV de los candidatos web: experiencia, formación e idiomas.

Cada función lee su consulta: las descripciones (motivo de baja, curso, nivel
educativo, idioma) salen de las tablas de referencia con JOIN.

Tablas:
    [CVExperiencia]  -> [CausalesBaja]
    [CVFormacion]    -> [CursosCarreras] -> [NivelesEducativos]
    [CVIdiomas]      -> [Competencias]
"""
from datetime import date

from apps.core.cache import cache_temporal
from apps.core.db import consultar

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


@cache_temporal()
def experiencia():
    """Una fila por trabajo declarado."""
    return _experiencia_sgo()


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


@cache_temporal()
def formacion():
    """Una fila por estudio declarado."""
    return _formacion_sgo()


# ==========================================================================
# Idiomas
# ==========================================================================
def _idiomas_sgo():
    return tuple({
        "web_user_id": int(r["WebUserId"]), "idioma": _texto(r["CompetenciaNombre"]),
        "nivel": int(r["CVIdiomaNivel"]), "anios": int(r["CVIdiomaAniosExp"] or 0),
    } for r in consultar(CONSULTA_IDIOMAS))


@cache_temporal()
def idiomas():
    """Una fila por idioma declarado."""
    return _idiomas_sgo()


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
