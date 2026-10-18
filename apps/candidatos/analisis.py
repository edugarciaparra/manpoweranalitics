"""
Análisis del módulo Candidatos: las pantallas de candidatos del SGO (can_res,
can_perpro, can_mov, can_geo, can_exp, can_dat, can_err, can_pru, can_ref,
canins y la búsqueda can_det) con el mismo SQL, filtros y registros en el modal.
"""
from apps.core import graficos as g
from apps.core import sgo
from apps.core.analisis import Catalogo, seccion
from apps.core.pantalla import (
    concentracion, decimal, detalle as respuesta_detalle, entero, etiquetas, extremos, kpi, lider, pct, proporcion,
    tabla, total, valores,
)
from apps.core.sgo import num

from . import services as s
from .services import DESEMPENO, EDAD, NOMBRE, contiene, where

catalogo = Catalogo()


def _orden(filas, orden, campo="label"):
    return sorted(filas, key=lambda r: orden.index(r[campo]) if r[campo] in orden else 99)


# ==========================================================================
# 1. Resumen general (can_res)
# ==========================================================================
_EDADES = ["18-24 años", "25-35 años", "36-45 años", "46-55 años", "56+ años"]
_CASE_EDAD = (f"CASE WHEN {EDAD} < 25 THEN '18-24 años' WHEN {EDAD} BETWEEN 25 AND 35 THEN '25-35 años' "
              f"WHEN {EDAD} BETWEEN 36 AND 45 THEN '36-45 años' WHEN {EDAD} BETWEEN 46 AND 55 THEN '46-55 años' ELSE '56+ años' END")


@catalogo.registrar(
    "resumen", "Resumen general",
    "Cuántos candidatos hay, cuántos se pueden asignar y cómo se distribuyen por sexo, edad, país, estado civil, educación y perfil.",
    usa_periodo=False, icono="bi-speedometer2", filtros=[s.F_PERFIL, s.F_PAIS, s.F_SEXO, s.F_ASIGNABLE],
)
def resumen(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_candidatos, SUM(CASE WHEN c.CandidatoNoAsignable = 'N' THEN 1 ELSE 0 END) AS candidatos_asignables,
               SUM(CASE WHEN c.CandidatoNoAsignable = 'S' THEN 1 ELSE 0 END) AS candidatos_no_asignables,
               ROUND(AVG(CASE WHEN {EDAD} BETWEEN 18 AND 80 THEN {EDAD} END), 0) AS edad_promedio,
               SUM(CASE WHEN c.CandidatoCarneSalud = 'S' AND c.CandidatoVencimientoCarneSalud >= GETDATE() THEN 1 ELSE 0 END) AS con_carne_vigente,
               ROUND(AVG({DESEMPENO}), 1) AS promedio_desempeno
        FROM dbo.Candidatos c WHERE {w}""", p)
    genero = sgo.filas(f"""
        SELECT CASE c.CandidatoSexo WHEN 'M' THEN 'Masculino' WHEN 'F' THEN 'Femenino' ELSE 'Sin especificar' END AS label, COUNT(*) AS value
        FROM dbo.Candidatos c WHERE {w} GROUP BY c.CandidatoSexo ORDER BY value DESC""", p)
    edades = _orden(sgo.filas(f"SELECT {_CASE_EDAD} AS label, COUNT(*) AS value FROM dbo.Candidatos c WHERE {w} GROUP BY {_CASE_EDAD}", p),
                    _EDADES)

    def por(join, id_col_c, id_col, desc):
        return sgo.filas(f"""SELECT RTRIM(x.{desc}) AS label, COUNT(*) AS value FROM dbo.Candidatos c
                             INNER JOIN dbo.{join} x ON c.{id_col_c} = x.{id_col}
                             WHERE {w} GROUP BY x.{id_col}, x.{desc} ORDER BY value DESC""", p)

    paises = por("Paises", "CandidatoResidenciaId", "PaisId", "PaisNombre")
    civiles = por("EstadosCiviles", "EstadoCivilId", "EstadoCivilId", "EstadoCivilDescripcion")
    niveles = por("NivelesEducativos", "NivelEducativoId", "NivelEducativoId", "NivelEducativoDescripcion")
    perfiles = por("PerfilesCandidatos", "PerfilCandidatoId", "PerfilCandidatoId", "PerfilCandidatoDescripcion")

    def bloque(titulo, filas, clave, explicacion, color=None, top=None):
        filas_g = filas[:top] if top else filas
        return seccion(titulo, [lider(filas, "label", "value", "candidatos"), concentracion(filas, "value", 3, "candidatos")],
                       g.ranking(etiquetas(filas_g), valores(filas_g, "value"), "Candidatos", color),
                       alto=g.alto_ranking(len(filas_g), 200), explicacion=explicacion, detalle=clave,
                       ayuda_detalle="Hacé clic en una barra para ver esos candidatos.")

    total_c = num(k.get("total_candidatos"))
    secciones = [
        seccion("Distribución por sexo", [lider(genero, "label", "value", "candidatos")],
                g.torta([(r["label"], num(r["value"])) for r in genero]), explicacion="Sexo registrado del candidato.",
                detalle="sexo", ayuda_detalle="Hacé clic en una porción para ver esos candidatos."),
        seccion("Distribución por rango de edad", [lider(edades, "label", "value", "candidatos")],
                g.columnas(etiquetas(edades), {"Candidatos": valores(edades, "value")}, rotar=0),
                explicacion="Edad actual según la fecha de nacimiento.", detalle="edad",
                ayuda_detalle="Hacé clic en un rango para ver esos candidatos."),
        bloque("Candidatos por país de residencia", paises, "pais", "País de residencia declarado.", g.SERIES[1], 15),
        bloque("Distribución por estado civil", civiles, "estado_civil", "Estado civil registrado.", g.SERIES[2]),
        bloque("Distribución por nivel educativo", niveles, "nivel", "Nivel educativo máximo registrado.", g.SERIES[3]),
        bloque("Candidatos por perfil profesional", perfiles, "perfil", "Perfil profesional asignado al candidato.", None, 20),
    ]
    return {
        "kpis": [
            kpi("Total candidatos", entero(total_c)),
            kpi("Asignables", entero(k.get("candidatos_asignables")), pct(proporcion(k.get("candidatos_asignables"), total_c))),
            kpi("No asignables", entero(k.get("candidatos_no_asignables")), "", "Marcados como no asignables (CandidatoNoAsignable = 'S')."),
            kpi("Edad promedio", f"{entero(k.get('edad_promedio'))} años", "", "Solo edades entre 18 y 80."),
            kpi("Con carné de salud vigente", entero(k.get("con_carne_vigente")), pct(proporcion(k.get("con_carne_vigente"), total_c))),
            kpi("Desempeño promedio", decimal(k.get("promedio_desempeno")), "", "Promedio de desempeño general registrado (mayor a 0)."),
        ],
        "conclusiones": [
            f"Hay {entero(total_c)} candidatos; {pct(proporcion(k.get('candidatos_asignables'), total_c))} son asignables.",
            lider(perfiles, "label", "value", "candidatos"),
            f"La edad promedio es de {entero(k.get('edad_promedio'))} años y {lider(edades, 'label', 'value', 'candidatos').lower()}",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué perfiles tienen más candidatos?", "¿Cuántos candidatos asignables hay?"],
        "contexto_ia": {"kpis": k, "genero": genero, "edades": edades, "perfiles": perfiles[:15], "niveles": niveles},
    }


def _condicion_basica(clave, valor):
    return {
        "sexo": ("c.CandidatoSexo = %s" if valor in ("Masculino", "Femenino") else "(c.CandidatoSexo NOT IN ('M', 'F') OR c.CandidatoSexo IS NULL)",
                 [{"Masculino": "M", "Femenino": "F"}[valor]] if valor in ("Masculino", "Femenino") else []),
        "edad": ({"18-24 años": f"{EDAD} < 25", "25-35 años": f"{EDAD} BETWEEN 25 AND 35", "36-45 años": f"{EDAD} BETWEEN 36 AND 45",
                  "46-55 años": f"{EDAD} BETWEEN 46 AND 55"}.get(valor, f"{EDAD} > 55"), []),
        "pais": ("RTRIM(pa.PaisNombre) = %s", [valor]),
        "estado_civil": ("RTRIM(ec.EstadoCivilDescripcion) = %s", [valor]),
        "nivel": ("RTRIM(ne.NivelEducativoDescripcion) = %s", [valor]),
        "perfil": ("RTRIM(pc.PerfilCandidatoDescripcion) = %s", [valor]),
    }.get(clave, ("1=0", []))


_JOIN_CIVIL = "LEFT JOIN dbo.EstadosCiviles ec ON c.EstadoCivilId = ec.EstadoCivilId"


@catalogo.detalle("resumen")
def detalle_resumen(clave, valor, serie, periodo, filtros):
    condicion, params = _condicion_basica(clave, valor)
    filas = s.candidatos(filtros, condicion, params, joins=_JOIN_CIVIL)
    return respuesta_detalle(f"Candidatos · {valor}", s.COLUMNAS_CANDIDATO, filas)


# ==========================================================================
# 2. Perfil profesional (can_perpro)
# ==========================================================================
_UNIVERSITARIO = f"({contiene('ne.NivelEducativoDescripcion', 'Universi')})"
_SECUNDARIA = (f"({_UNIVERSITARIO} OR {contiene('ne.NivelEducativoDescripcion', 'Terciari')} "
               f"OR {contiene('ne.NivelEducativoDescripcion', 'Tecnicatura')} "
               f"OR ({contiene('ne.NivelEducativoDescripcion', 'Bachillerato')} AND {contiene('ne.NivelEducativoDescripcion', 'Complet')}) "
               f"OR ({contiene('ne.NivelEducativoDescripcion', 'Liceo')} AND {contiene('ne.NivelEducativoDescripcion', 'Complet')}) "
               f"OR ({contiene('ne.NivelEducativoDescripcion', 'Secundari')} AND NOT {contiene('ne.NivelEducativoDescripcion', 'Incomplet')}))")
_EDADES_CORTAS = ["18-24", "25-35", "36-45", "46-55", "56+"]
_CASE_EDAD_CORTA = (f"CASE WHEN {EDAD} < 25 THEN '18-24' WHEN {EDAD} BETWEEN 25 AND 35 THEN '25-35' WHEN {EDAD} BETWEEN 36 AND 45 "
                    f"THEN '36-45' WHEN {EDAD} BETWEEN 46 AND 55 THEN '46-55' ELSE '56+' END")
JOIN_NIVEL = "INNER JOIN dbo.NivelesEducativos ne ON c.NivelEducativoId = ne.NivelEducativoId"
JOIN_PERFIL = "INNER JOIN dbo.PerfilesCandidatos pc ON c.PerfilCandidatoId = pc.PerfilCandidatoId"


@catalogo.registrar(
    "perfil", "Perfil profesional",
    "Perfiles y nivel educativo de los candidatos, cómo se cruzan, su desempeño y la composición por edad de cada perfil.",
    usa_periodo=False, icono="bi-mortarboard", filtros=[s.F_PERFIL, s.F_NIVEL, s.F_PAIS],
)
def perfil(periodo, filtros):
    w, p = where(filtros)
    wc2, pc2 = where(filtros, "c2")
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_candidatos, COUNT(DISTINCT c.PerfilCandidatoId) AS perfiles_distintos,
               SUM(CASE WHEN {_UNIVERSITARIO} THEN 1 ELSE 0 END) AS con_universitario,
               SUM(CASE WHEN {_SECUNDARIA} THEN 1 ELSE 0 END) AS con_secundaria_completa,
               ROUND(AVG({DESEMPENO}), 1) AS promedio_desempeno
        FROM dbo.Candidatos c {JOIN_NIVEL} WHERE {w}""", p)
    con_entrevista = num(sgo.valor(f"""SELECT COUNT(DISTINCT e.CandidatoId) AS con_experiencia FROM dbo.Entrevistas e
                                        INNER JOIN dbo.Candidatos c2 ON e.CandidatoId = c2.CandidatoId WHERE {wc2}""", pc2))
    perfiles = sgo.filas(f"""
        SELECT RTRIM(pc.PerfilCandidatoDescripcion) AS label, COUNT(*) AS value, ROUND(AVG({DESEMPENO}), 1) AS desempeno_promedio
        FROM dbo.Candidatos c {JOIN_PERFIL} WHERE {w}
        GROUP BY pc.PerfilCandidatoId, pc.PerfilCandidatoDescripcion ORDER BY value DESC""", p)
    niveles = sgo.filas(f"""SELECT RTRIM(ne.NivelEducativoDescripcion) AS label, COUNT(*) AS value FROM dbo.Candidatos c {JOIN_NIVEL}
                            WHERE {w} GROUP BY ne.NivelEducativoId, ne.NivelEducativoDescripcion ORDER BY value DESC""", p)
    cruce = sgo.filas(f"""
        SELECT RTRIM(pc.PerfilCandidatoDescripcion) AS perfil, RTRIM(ne.NivelEducativoDescripcion) AS nivel, COUNT(*) AS cantidad
        FROM dbo.Candidatos c {JOIN_PERFIL} {JOIN_NIVEL} WHERE {w}
        GROUP BY pc.PerfilCandidatoId, pc.PerfilCandidatoDescripcion, ne.NivelEducativoId, ne.NivelEducativoDescripcion
        HAVING COUNT(*) >= 3""", p)
    desempeno = sgo.filas(f"""
        SELECT TOP 15 RTRIM(pc.PerfilCandidatoDescripcion) AS label, COUNT(*) AS total_candidatos,
               ROUND(AVG({DESEMPENO}), 2) AS desempeno_promedio, MIN(c.CandidatoPromedioDesemGral) AS desempeno_minimo,
               MAX(c.CandidatoPromedioDesemGral) AS desempeno_maximo
        FROM dbo.Candidatos c {JOIN_PERFIL} WHERE {w} AND c.CandidatoPromedioDesemGral > 0
        GROUP BY pc.PerfilCandidatoId, pc.PerfilCandidatoDescripcion HAVING COUNT(*) >= 5 ORDER BY desempeno_promedio DESC""", p)
    piramide = sgo.filas(f"""
        WITH PerfilTotales AS (SELECT TOP 6 c.PerfilCandidatoId FROM dbo.Candidatos c WHERE {w}
                               GROUP BY c.PerfilCandidatoId HAVING COUNT(*) >= 10 ORDER BY COUNT(*) DESC)
        SELECT RTRIM(pc.PerfilCandidatoDescripcion) AS perfil, {_CASE_EDAD_CORTA} AS rango_edad, COUNT(*) AS cantidad
        FROM dbo.Candidatos c {JOIN_PERFIL} INNER JOIN PerfilTotales pt ON c.PerfilCandidatoId = pt.PerfilCandidatoId
        WHERE {w} GROUP BY pc.PerfilCandidatoDescripcion, {_CASE_EDAD_CORTA}""", p + p)
    universitarios = sgo.filas(f"""
        SELECT TOP 10 RTRIM(pc.PerfilCandidatoDescripcion) AS label, COUNT(*) AS total_candidatos,
               SUM(CASE WHEN {_UNIVERSITARIO} THEN 1 ELSE 0 END) AS con_universitario,
               ROUND(CAST(SUM(CASE WHEN {_UNIVERSITARIO} THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 2) AS pct_universitario
        FROM dbo.Candidatos c {JOIN_PERFIL} {JOIN_NIVEL} WHERE {w}
        GROUP BY pc.PerfilCandidatoId, pc.PerfilCandidatoDescripcion HAVING COUNT(*) >= 5 ORDER BY pct_universitario DESC""", p)

    top_perfiles = [r["label"] for r in perfiles[:12]]
    top_niveles = [r["label"] for r in niveles[:8]]
    celdas = [[top_niveles.index(r["nivel"]), top_perfiles.index(r["perfil"]), num(r["cantidad"])]
              for r in cruce if r["perfil"] in top_perfiles and r["nivel"] in top_niveles]
    perfiles_p = list(dict.fromkeys(r["perfil"] for r in piramide))
    series_p = {e: [next((num(r["cantidad"]) for r in piramide if r["perfil"] == pf and r["rango_edad"] == e), 0) for pf in perfiles_p]
                for e in _EDADES_CORTAS}
    total_c = num(k.get("total_candidatos"))
    secciones = [
        seccion("Candidatos por perfil profesional", [lider(perfiles, "label", "value", "candidatos"),
                                                      concentracion(perfiles, "value", 5, "candidatos")],
                g.ranking(etiquetas(perfiles[:20]), valores(perfiles[:20], "value"), "Candidatos"), alto=g.alto_ranking(min(20, len(perfiles))),
                explicacion="Los 20 perfiles con más candidatos.", detalle="perfil",
                ayuda_detalle="Hacé clic en un perfil para ver sus candidatos."),
        seccion("Nivel educativo detallado", [lider(niveles, "label", "value", "candidatos")],
                g.ranking(etiquetas(niveles), valores(niveles, "value"), "Candidatos", g.SERIES[2]), alto=g.alto_ranking(len(niveles)),
                explicacion="Candidatos por nivel educativo registrado.", detalle="nivel",
                ayuda_detalle="Hacé clic en un nivel para ver esos candidatos."),
        seccion("Cruce perfil × nivel educativo", ["Las celdas más oscuras son las combinaciones más frecuentes."],
                g.mapa_calor(top_niveles, top_perfiles, celdas), alto=max(340, 30 * len(top_perfiles) + 130),
                explicacion="Candidatos de cada perfil (filas, los 12 principales) según su nivel educativo (columnas, los 8 principales)."),
        seccion("Desempeño promedio por perfil", [extremos(desempeno, "label", "desempeno_promedio", decimal, "mejor desempeño", "peor")],
                g.ranking(etiquetas(desempeno), valores(desempeno, "desempeno_promedio"), "Desempeño promedio", g.SERIES[1]),
                alto=g.alto_ranking(len(desempeno)),
                explicacion="Promedio de desempeño general de los candidatos evaluados de cada perfil (5 o más).", detalle="perfil",
                ayuda_detalle="Hacé clic en un perfil para ver sus candidatos."),
        seccion("Composición por edad de los 6 perfiles principales", [],
                g.columnas(perfiles_p, series_p, apiladas=True), alto=360,
                explicacion="Candidatos de cada perfil apilados por rango de edad.", detalle="perfil",
                ayuda_detalle="Hacé clic en un perfil para ver sus candidatos."),
        seccion("Perfiles con más educación universitaria", [extremos(universitarios, "label", "pct_universitario", pct, "mayor", "menor")],
                g.ranking(etiquetas(universitarios), valores(universitarios, "pct_universitario"), "% universitarios", g.SERIES[3],
                          formato="fmt:pct"),
                alto=g.alto_ranking(len(universitarios)),
                explicacion="Parte de los candidatos de cada perfil (5 o más) con nivel universitario."),
    ]
    return {
        "kpis": [
            kpi("Total candidatos", entero(total_c)),
            kpi("Perfiles distintos", entero(k.get("perfiles_distintos"))),
            kpi("Con educación universitaria", entero(k.get("con_universitario")), pct(proporcion(k.get("con_universitario"), total_c))),
            kpi("Secundaria completa o más", entero(k.get("con_secundaria_completa")),
                pct(proporcion(k.get("con_secundaria_completa"), total_c))),
            kpi("Con al menos una entrevista", entero(con_entrevista), pct(proporcion(con_entrevista, total_c))),
            kpi("Desempeño promedio", decimal(k.get("promedio_desempeno"))),
        ],
        "conclusiones": [
            lider(perfiles, "label", "value", "candidatos"),
            f"{pct(proporcion(k.get('con_universitario'), total_c))} tiene educación universitaria y "
            f"{pct(proporcion(k.get('con_secundaria_completa'), total_c))} al menos secundaria completa.",
            extremos(desempeno, "label", "desempeno_promedio", decimal, "perfil de mejor desempeño", "peor"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué perfiles tienen mejor desempeño?", "¿Qué nivel educativo predomina?"],
        "contexto_ia": {"kpis": k, "perfiles": perfiles[:15], "niveles": niveles, "desempeno": desempeno},
    }


@catalogo.detalle("perfil")
def detalle_perfil(clave, valor, serie, periodo, filtros):
    condicion, params = _condicion_basica(clave, valor)
    if clave == "perfil" and serie in _EDADES_CORTAS:
        condicion += " AND " + {"18-24": f"{EDAD} < 25", "25-35": f"{EDAD} BETWEEN 25 AND 35", "36-45": f"{EDAD} BETWEEN 36 AND 45",
                                "46-55": f"{EDAD} BETWEEN 46 AND 55"}.get(serie, f"{EDAD} > 55")
    filas = s.candidatos(filtros, condicion, params)
    return respuesta_detalle(f"Candidatos · {valor}" + (f" · {serie}" if serie in _EDADES_CORTAS else ""), s.COLUMNAS_CANDIDATO, filas)


# ==========================================================================
# 3. Disponibilidad y movilidad (can_mov)
# ==========================================================================
_SI = "= 'S'"
_N_DISP = (f"(CASE WHEN c.CandidatoZafrales = 'S' THEN 1 ELSE 0 END + CASE WHEN c.CandidatoHorarioRotativo = 'S' THEN 1 ELSE 0 END "
           f"+ CASE WHEN c.CandidatoDisponibilidadHoraria = 'S' THEN 1 ELSE 0 END)")
_FLEX = ["Muy flexible (3/3)", "Flexible (2/3)", "Poco flexible (1/3)", "Rígido (0/3)"]
_CASE_FLEX = (f"CASE WHEN {_N_DISP} = 3 THEN '{_FLEX[0]}' WHEN {_N_DISP} = 2 THEN '{_FLEX[1]}' "
              f"WHEN {_N_DISP} = 1 THEN '{_FLEX[2]}' ELSE '{_FLEX[3]}' END")
_CAMPOS_DISP = [("Libreta", "c.CandidatoLibretaConducir"), ("Zafrales", "c.CandidatoZafrales"),
                ("Rotativo", "c.CandidatoHorarioRotativo"), ("Disp. horaria", "c.CandidatoDisponibilidadHoraria")]
_CASE_COMBO = " + ".join(f"CASE WHEN {col} = 'S' THEN '{nom} · ' ELSE '' END" for nom, col in _CAMPOS_DISP)
COLUMNAS_DISP = ["Candidato Id", "Candidato", "Perfil", "País", "Libreta", "Zafrales", "Rotativo", "Disp. horaria"]


def _candidatos_disp(filtros, condicion, params=None, joins=""):
    w, p = where(filtros)
    return sgo.filas(f"""
        SELECT TOP 500 c.CandidatoId, {NOMBRE} AS candidato, RTRIM(pc.PerfilCandidatoDescripcion) AS perfil, RTRIM(pa.PaisNombre) AS pais,
               CASE WHEN c.CandidatoLibretaConducir = 'S' THEN 'Sí' ELSE 'No' END AS libreta,
               CASE WHEN c.CandidatoZafrales = 'S' THEN 'Sí' ELSE 'No' END AS zafrales,
               CASE WHEN c.CandidatoHorarioRotativo = 'S' THEN 'Sí' ELSE 'No' END AS rotativo,
               CASE WHEN c.CandidatoDisponibilidadHoraria = 'S' THEN 'Sí' ELSE 'No' END AS disp_horaria
        FROM dbo.Candidatos c LEFT JOIN dbo.PerfilesCandidatos pc ON c.PerfilCandidatoId = pc.PerfilCandidatoId
        LEFT JOIN dbo.Paises pa ON c.CandidatoResidenciaId = pa.PaisId {joins}
        WHERE {w} AND ({condicion}) ORDER BY c.CandidatoApellido, c.CandidatoNombre""", p + list(params or []))


@catalogo.registrar(
    "disponibilidad", "Disponibilidad y movilidad",
    "Quiénes tienen libreta, aceptan zafrales, horario rotativo o disponibilidad total, y qué tan flexibles son.",
    usa_periodo=False, icono="bi-car-front", filtros=[s.F_PERFIL, s.F_PAIS, s.F_DEPTO, s.F_LIBRETA],
)
def disponibilidad(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_candidatos, SUM(CASE WHEN c.CandidatoLibretaConducir = 'S' THEN 1 ELSE 0 END) AS con_libreta,
               SUM(CASE WHEN c.CandidatoZafrales = 'S' THEN 1 ELSE 0 END) AS acepta_zafrales,
               SUM(CASE WHEN c.CandidatoHorarioRotativo = 'S' THEN 1 ELSE 0 END) AS acepta_rotativo,
               SUM(CASE WHEN c.CandidatoDisponibilidadHoraria = 'S' THEN 1 ELSE 0 END) AS disponibilidad_total,
               SUM(CASE WHEN c.CandidatoLibretaConducir = 'S' AND {_N_DISP} = 3 THEN 1 ELSE 0 END) AS super_flexibles
        FROM dbo.Candidatos c WHERE {w}""", p)
    libretas = sgo.filas(f"""
        SELECT RTRIM(cl.CategoriaLibretaConducirDescri) AS label, COUNT(*) AS value
        FROM dbo.Candidatos c INNER JOIN dbo.CategoriasLibretaConducir cl ON c.CategoriaLibretaConducirId = cl.CategoriaLibretaConducirId
        WHERE {w} AND c.CandidatoLibretaConducir = 'S'
        GROUP BY cl.CategoriaLibretaConducirId, cl.CategoriaLibretaConducirDescri ORDER BY value DESC""", p)
    flex = _orden(sgo.filas(f"SELECT {_CASE_FLEX} AS label, COUNT(*) AS value FROM dbo.Candidatos c WHERE {w} GROUP BY {_CASE_FLEX}", p), _FLEX)
    por_perfil = sgo.filas(f"""
        SELECT TOP 10 RTRIM(pc.PerfilCandidatoDescripcion) AS label, COUNT(*) AS total_candidatos,
               SUM(CASE WHEN c.CandidatoLibretaConducir = 'S' THEN 1 ELSE 0 END) AS con_libreta,
               SUM(CASE WHEN c.CandidatoZafrales = 'S' THEN 1 ELSE 0 END) AS zafrales,
               SUM(CASE WHEN c.CandidatoHorarioRotativo = 'S' THEN 1 ELSE 0 END) AS rotativo,
               SUM(CASE WHEN c.CandidatoDisponibilidadHoraria = 'S' THEN 1 ELSE 0 END) AS disp_horaria,
               ROUND(CAST(SUM(CASE WHEN c.CandidatoLibretaConducir = 'S' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 1) AS pct_libreta
        FROM dbo.Candidatos c {JOIN_PERFIL} WHERE {w}
        GROUP BY pc.PerfilCandidatoId, pc.PerfilCandidatoDescripcion HAVING COUNT(*) >= 10 ORDER BY pct_libreta DESC""", p)
    combos = sgo.filas(f"""
        SELECT TOP 6 {_CASE_COMBO} AS label, COUNT(*) AS value FROM dbo.Candidatos c
        WHERE {w} AND (c.CandidatoLibretaConducir = 'S' OR c.CandidatoZafrales = 'S' OR c.CandidatoHorarioRotativo = 'S'
                       OR c.CandidatoDisponibilidadHoraria = 'S')
        GROUP BY {_CASE_COMBO} HAVING COUNT(*) >= 5 ORDER BY value DESC""", p)
    for r in combos:
        r["label"] = str(r["label"]).strip().rstrip("·").strip() or "Sin datos"
    paises = sgo.filas(f"""
        SELECT TOP 10 RTRIM(pa.PaisNombre) AS label, COUNT(*) AS total_candidatos,
               SUM(CASE WHEN c.CandidatoLibretaConducir = 'S' THEN 1 ELSE 0 END) AS con_libreta,
               ROUND(CAST(SUM(CASE WHEN c.CandidatoLibretaConducir = 'S' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 1) AS pct_libreta
        FROM dbo.Candidatos c INNER JOIN dbo.Paises pa ON c.CandidatoResidenciaId = pa.PaisId
        WHERE {w} GROUP BY pa.PaisId, pa.PaisNombre HAVING COUNT(*) >= 10 ORDER BY total_candidatos DESC""", p)

    total_c = num(k.get("total_candidatos"))
    general = [("Con libreta", num(k.get("con_libreta"))), ("Zafrales", num(k.get("acepta_zafrales"))),
               ("Horario rotativo", num(k.get("acepta_rotativo"))), ("Disponibilidad horaria", num(k.get("disponibilidad_total")))]
    secciones = [
        seccion("Distribución de disponibilidades", [f"{pct(proporcion(v, total_c))} {e.lower()}." for e, v in general[:2]],
                g.columnas([e for e, _ in general], {"Candidatos": [v for _, v in general]}, rotar=0),
                explicacion="Candidatos que tienen libreta de conducir, aceptan trabajos zafrales, horario rotativo o tienen "
                            "disponibilidad horaria total. Un candidato puede estar en varias barras.",
                detalle="general", ayuda_detalle="Hacé clic en una barra para ver esos candidatos."),
        seccion("Nivel de flexibilidad", [lider(flex, "label", "value", "candidatos")],
                g.columnas(etiquetas(flex), {"Candidatos": valores(flex, "value")}, rotar=0, colores=[g.SERIES[2]]),
                explicacion="Cuántas de las tres disponibilidades (zafrales, rotativo, horaria) acepta cada candidato.",
                detalle="flexibilidad", ayuda_detalle="Hacé clic en un nivel para ver esos candidatos."),
        seccion("Categorías de libreta de conducir", [lider(libretas, "label", "value", "candidatos")],
                g.ranking(etiquetas(libretas), valores(libretas, "value"), "Candidatos", g.SERIES[1]), alto=g.alto_ranking(len(libretas), 200),
                explicacion="Categoría de libreta de los candidatos que tienen libreta.", detalle="libreta",
                ayuda_detalle="Hacé clic en una categoría para ver esos candidatos."),
        seccion("Combinaciones más comunes", [lider(combos, "label", "value", "candidatos")],
                g.ranking(etiquetas(combos), valores(combos, "value"), "Candidatos", g.SERIES[3]), alto=g.alto_ranking(len(combos), 200),
                explicacion="Combinaciones de disponibilidades más frecuentes entre los que tienen al menos una.", detalle="combinacion",
                ayuda_detalle="Hacé clic en una combinación para ver esos candidatos."),
        seccion("Disponibilidad por perfil (top 10 por % con libreta)", [],
                g.columnas(etiquetas(por_perfil), {"Libreta": valores(por_perfil, "con_libreta"), "Zafrales": valores(por_perfil, "zafrales"),
                                                   "Rotativo": valores(por_perfil, "rotativo"),
                                                   "Disp. horaria": valores(por_perfil, "disp_horaria")}), alto=360,
                explicacion="Para los 10 perfiles (10+ candidatos) con mayor % de libreta: cuántos candidatos tienen cada disponibilidad.",
                detalle="perfil", ayuda_detalle="Hacé clic en un perfil para ver sus candidatos."),
        seccion("Movilidad por país de residencia", [extremos(paises, "label", "pct_libreta", pct, "mayor % con libreta", "menor")],
                g.ranking(etiquetas(paises), valores(paises, "pct_libreta"), "% con libreta", formato="fmt:pct"),
                alto=g.alto_ranking(len(paises), 200),
                explicacion="Parte de los candidatos de cada país (10 o más) que tiene libreta de conducir.", detalle="pais",
                ayuda_detalle="Hacé clic en un país para ver sus candidatos."),
    ]
    return {
        "kpis": [
            kpi("Total candidatos", entero(total_c)),
            kpi("Con libreta", entero(k.get("con_libreta")), pct(proporcion(k.get("con_libreta"), total_c))),
            kpi("Aceptan zafrales", entero(k.get("acepta_zafrales")), pct(proporcion(k.get("acepta_zafrales"), total_c))),
            kpi("Aceptan rotativo", entero(k.get("acepta_rotativo")), pct(proporcion(k.get("acepta_rotativo"), total_c))),
            kpi("Disponibilidad horaria", entero(k.get("disponibilidad_total")), pct(proporcion(k.get("disponibilidad_total"), total_c))),
            kpi("Súper flexibles", entero(k.get("super_flexibles")), "las 4 disponibilidades",
                "Tienen libreta y aceptan zafrales, rotativo y disponibilidad horaria."),
        ],
        "conclusiones": [
            f"{pct(proporcion(k.get('con_libreta'), total_c))} tiene libreta y {pct(proporcion(k.get('acepta_zafrales'), total_c))} acepta zafrales.",
            f"{entero(k.get('super_flexibles'))} candidatos cumplen las cuatro disponibilidades.",
            lider(flex, "label", "value", "candidatos"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Cuántos candidatos aceptan zafrales y rotativo?", "¿Qué perfiles tienen más libreta?"],
        "contexto_ia": {"kpis": k, "flexibilidad": flex, "libretas": libretas, "combinaciones": combos},
    }


@catalogo.detalle("disponibilidad")
def detalle_disponibilidad(clave, valor, serie, periodo, filtros):
    params, joins = [], ""
    if clave == "general":
        condicion = {"Con libreta": "c.CandidatoLibretaConducir = 'S'", "Zafrales": "c.CandidatoZafrales = 'S'",
                     "Horario rotativo": "c.CandidatoHorarioRotativo = 'S'"}.get(valor, "c.CandidatoDisponibilidadHoraria = 'S'")
    elif clave == "flexibilidad":
        condicion = f"{_N_DISP} = %s"
        params = [3 - _FLEX.index(valor) if valor in _FLEX else -1]
    elif clave == "libreta":
        condicion = "c.CandidatoLibretaConducir = 'S' AND RTRIM(cl.CategoriaLibretaConducirDescri) = %s"
        params = [valor]
        joins = "LEFT JOIN dbo.CategoriasLibretaConducir cl ON c.CategoriaLibretaConducirId = cl.CategoriaLibretaConducirId"
    elif clave == "combinacion":
        partes = [x.strip() for x in valor.split("·")]
        condicion = " AND ".join(f"{col} = 'S'" if nom in partes else f"({col} != 'S' OR {col} IS NULL)" for nom, col in _CAMPOS_DISP)
    elif clave == "perfil":
        condicion, params = "RTRIM(pc.PerfilCandidatoDescripcion) = %s", [valor]
        if serie:
            col = dict((n if n != "Disp. horaria" else "Disp. horaria", c) for n, c in _CAMPOS_DISP).get(serie)
            if col:
                condicion += f" AND {col} = 'S'"
    else:
        condicion, params = "RTRIM(pa.PaisNombre) = %s", [valor]
    return respuesta_detalle(f"Candidatos · {valor}" + (f" · {serie}" if clave == "perfil" and serie else ""), COLUMNAS_DISP,
                             _candidatos_disp(filtros, condicion, params, joins))


# ==========================================================================
# 4. Análisis geográfico (can_geo)
# ==========================================================================
COLUMNAS_GEO = ["Candidato Id", "Candidato", "Perfil", "Departamento", "Localidad", "Nacionalidad", "Residencia"]


def _candidatos_geo(filtros, condicion, params):
    w, p = where(filtros)
    return sgo.filas(f"""
        SELECT TOP 500 c.CandidatoId, {NOMBRE} AS candidato, RTRIM(pc.PerfilCandidatoDescripcion) AS perfil,
               RTRIM(d.DepartamentoNombre) AS departamento, RTRIM(l.LocalidadNombre) AS localidad,
               RTRIM(pn.PaisNombre) AS nacionalidad, RTRIM(pr.PaisNombre) AS residencia
        FROM dbo.Candidatos c LEFT JOIN dbo.PerfilesCandidatos pc ON c.PerfilCandidatoId = pc.PerfilCandidatoId
        LEFT JOIN dbo.Departamentos d ON c.CandidatoDepartamentoId = d.DepartamentoId
        LEFT JOIN dbo.Localidades l ON c.CandidatoLocalidadId = l.LocalidadId
        LEFT JOIN dbo.Paises pn ON c.CandidatoNacionalidadId = pn.PaisId
        LEFT JOIN dbo.Paises pr ON c.CandidatoResidenciaId = pr.PaisId
        WHERE {w} AND ({condicion}) ORDER BY c.CandidatoApellido, c.CandidatoNombre""", p + list(params))


@catalogo.registrar(
    "geografico", "Análisis geográfico",
    "Dónde viven los candidatos: departamentos, localidades, nacionalidades, país de residencia y movilidad internacional.",
    usa_periodo=False, icono="bi-geo-alt", filtros=[s.F_PERFIL, s.F_DEPTO, s.F_PAIS],
)
def geografico(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_candidatos, COUNT(DISTINCT c.CandidatoDepartamentoId) AS departamentos_distintos,
               COUNT(DISTINCT c.CandidatoLocalidadId) AS localidades_distintas, COUNT(DISTINCT c.CandidatoNacionalidadId) AS nacionalidades_distintas,
               COUNT(DISTINCT c.CandidatoResidenciaId) AS paises_residencia_distintos,
               COUNT(DISTINCT CASE WHEN c.CandidatoResidenciaId != c.CandidatoNacionalidadId THEN c.CandidatoId END) AS extranjeros_residentes
        FROM dbo.Candidatos c WHERE {w}""", p)
    deptos = sgo.filas(f"""
        SELECT TOP 15 RTRIM(d.DepartamentoNombre) AS label, COUNT(*) AS value, COUNT(DISTINCT c.CandidatoLocalidadId) AS localidades
        FROM dbo.Candidatos c INNER JOIN dbo.Departamentos d ON c.CandidatoDepartamentoId = d.DepartamentoId
        WHERE {w} GROUP BY d.DepartamentoId, d.DepartamentoNombre ORDER BY value DESC""", p)
    localidades = sgo.filas(f"""
        SELECT TOP 20 RTRIM(l.LocalidadNombre) AS label, RTRIM(d.DepartamentoNombre) AS departamento, COUNT(*) AS value
        FROM dbo.Candidatos c INNER JOIN dbo.Localidades l ON c.CandidatoLocalidadId = l.LocalidadId
        LEFT JOIN dbo.Departamentos d ON c.CandidatoDepartamentoId = d.DepartamentoId
        WHERE {w} GROUP BY l.LocalidadId, l.LocalidadNombre, d.DepartamentoNombre ORDER BY value DESC""", p)
    nac_res = sgo.filas(f"""
        SELECT TOP 10 RTRIM(pn.PaisNombre) AS nacionalidad, RTRIM(pr.PaisNombre) AS residencia, COUNT(*) AS cantidad
        FROM dbo.Candidatos c INNER JOIN dbo.Paises pn ON c.CandidatoNacionalidadId = pn.PaisId
        INNER JOIN dbo.Paises pr ON c.CandidatoResidenciaId = pr.PaisId
        WHERE {w} GROUP BY pn.PaisNombre, pr.PaisNombre HAVING COUNT(*) >= 3 ORDER BY cantidad DESC""", p)
    nacionalidades = sgo.filas(f"""
        SELECT TOP 10 RTRIM(pa.PaisNombre) AS label, COUNT(*) AS value
        FROM dbo.Candidatos c INNER JOIN dbo.Paises pa ON c.CandidatoNacionalidadId = pa.PaisId
        WHERE {w} GROUP BY pa.PaisId, pa.PaisNombre ORDER BY value DESC""", p)
    residencias = sgo.filas(f"""
        SELECT TOP 10 RTRIM(pa.PaisNombre) AS label, COUNT(*) AS value, COUNT(DISTINCT c.CandidatoNacionalidadId) AS nacionalidades_diferentes
        FROM dbo.Candidatos c INNER JOIN dbo.Paises pa ON c.CandidatoResidenciaId = pa.PaisId
        WHERE {w} GROUP BY pa.PaisId, pa.PaisNombre ORDER BY value DESC""", p)
    movilidad = sgo.filas(f"""
        SELECT CASE WHEN c.CandidatoResidenciaId = c.CandidatoNacionalidadId THEN 'Mismo país' ELSE 'País diferente' END AS label,
               COUNT(*) AS value
        FROM dbo.Candidatos c WHERE {w}
        GROUP BY CASE WHEN c.CandidatoResidenciaId = c.CandidatoNacionalidadId THEN 'Mismo país' ELSE 'País diferente' END""", p)

    total_c = num(k.get("total_candidatos"))
    top5 = total(sorted(deptos, key=lambda r: -num(r["value"]))[:5], "value")
    secciones = [
        seccion("Top 15 departamentos", [lider(deptos, "label", "value", "candidatos", "el top 15")],
                g.ranking(etiquetas(deptos), valores(deptos, "value"), "Candidatos"), alto=g.alto_ranking(len(deptos)),
                explicacion="Departamento de residencia del candidato.", detalle="departamento",
                ayuda_detalle="Hacé clic en un departamento para ver sus candidatos."),
        seccion("Top 20 localidades", [lider(localidades, "label", "value", "candidatos", "el top 20")],
                g.ranking([f"{r['label']} ({r['departamento']})" if r.get("departamento") else r["label"] for r in localidades],
                          valores(localidades, "value"), "Candidatos", g.SERIES[1]), alto=g.alto_ranking(len(localidades)),
                explicacion="Localidad de residencia, con su departamento entre paréntesis.", detalle="localidad",
                ayuda_detalle="Hacé clic en una localidad para ver sus candidatos."),
        seccion("Distribución por nacionalidad", [lider(nacionalidades, "label", "value", "candidatos")],
                g.ranking(etiquetas(nacionalidades), valores(nacionalidades, "value"), "Candidatos", g.SERIES[2]),
                alto=g.alto_ranking(len(nacionalidades), 200), explicacion="País de nacionalidad.", detalle="nacionalidad",
                ayuda_detalle="Hacé clic en una nacionalidad para ver esos candidatos."),
        seccion("Países de residencia actual", [lider(residencias, "label", "value", "candidatos")],
                g.ranking(etiquetas(residencias), valores(residencias, "value"), "Candidatos", g.SERIES[3]),
                alto=g.alto_ranking(len(residencias), 200), explicacion="País donde vive hoy el candidato.", detalle="residencia",
                ayuda_detalle="Hacé clic en un país para ver esos candidatos."),
        seccion("Movilidad geográfica internacional",
                [f"{entero(k.get('extranjeros_residentes'))} candidatos viven en un país distinto al de su nacionalidad."],
                g.torta([(r["label"], num(r["value"])) for r in movilidad], colores=[g.SERIES[0], g.SERIES[1]]),
                explicacion="Compara el país de residencia con el de nacionalidad.",
                tabla=tabla("Nacionalidad → residencia (top 10)", ["Nacionalidad", "Residencia", "Candidatos"],
                            [[r["nacionalidad"], r["residencia"], entero(r["cantidad"])] for r in nac_res])),
        seccion("Concentración geográfica (top 5 departamentos)",
                [f"Los 5 departamentos con más candidatos concentran el {pct(proporcion(top5, total_c))} del total."],
                g.torta([("Top 5 departamentos", top5), ("Resto", max(0, total_c - top5))], colores=[g.SERIES[0], g.NEUTRO]),
                explicacion="Qué parte de los candidatos vive en los 5 departamentos principales."),
    ]
    return {
        "kpis": [
            kpi("Total candidatos", entero(total_c)),
            kpi("Departamentos", entero(k.get("departamentos_distintos"))),
            kpi("Localidades", entero(k.get("localidades_distintas"))),
            kpi("Nacionalidades", entero(k.get("nacionalidades_distintas"))),
            kpi("Países de residencia", entero(k.get("paises_residencia_distintos"))),
            kpi("Extranjeros residentes", entero(k.get("extranjeros_residentes")), pct(proporcion(k.get("extranjeros_residentes"), total_c))),
        ],
        "conclusiones": [
            lider(deptos, "label", "value", "candidatos", "el top 15"),
            f"Los 5 departamentos principales concentran el {pct(proporcion(top5, total_c))} de los candidatos.",
            f"{entero(k.get('extranjeros_residentes'))} candidatos residen fuera de su país de nacionalidad.",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Dónde se concentran los candidatos?", "¿Cuántos candidatos extranjeros hay?"],
        "contexto_ia": {"kpis": k, "departamentos": deptos, "nacionalidades": nacionalidades},
    }


@catalogo.detalle("geografico")
def detalle_geografico(clave, valor, serie, periodo, filtros):
    if clave == "localidad":
        valor_l = valor.split(" (")[0]
        condicion, params = "RTRIM(l.LocalidadNombre) = %s", [valor_l]
    else:
        columna = {"departamento": "d.DepartamentoNombre", "nacionalidad": "pn.PaisNombre"}.get(clave, "pr.PaisNombre")
        condicion, params = f"RTRIM({columna}) = %s", [valor]
    return respuesta_detalle(f"Candidatos · {valor}", COLUMNAS_GEO, _candidatos_geo(filtros, condicion, params))


# ==========================================================================
# 5. Experiencia y trayectoria (can_exp)
# ==========================================================================
_CALIF = "(CAST(e.EntrevistaPuntajeFormacion AS FLOAT) + CAST(e.EntrevistaPuntajeExperiencia AS FLOAT))"
_N_ENT = "(SELECT COUNT(*) FROM dbo.Entrevistas ez WHERE ez.CandidatoId = c.CandidatoId)"
_RANGOS_ENT = [("Sin entrevistas", "= 0"), ("1 entrevista", "= 1"), ("2-3 entrevistas", "BETWEEN 2 AND 3"),
               ("4-5 entrevistas", "BETWEEN 4 AND 5"), ("6-10 entrevistas", "BETWEEN 6 AND 10"), ("Más de 10", "> 10")]
_RANGOS_CALIF = [("Excelente (9-10)", 9, 10), ("Bueno (7-8)", 7, 8.99), ("Regular (5-6)", 5, 6.99), ("Bajo (3-4)", 3, 4.99),
                 ("Muy bajo (0-2)", 0, 2.99)]
COLUMNAS_EXP = ["Candidato Id", "Candidato", "Perfil", "Entrevistas", "Calificación promedio"]


@catalogo.registrar(
    "experiencia", "Experiencia y trayectoria",
    "Cuántas entrevistas tuvo cada candidato, qué calificaciones obtuvo, por perfil, y cómo evolucionó en los últimos años.",
    usa_periodo=False, icono="bi-briefcase", filtros=[s.F_PERFIL, s.F_PAIS, s.F_DEPTO, s.F_EXPERIENCIA],
)
def experiencia(periodo, filtros):
    w, p = where(filtros)
    total_c = num(sgo.valor(f"SELECT COUNT(*) AS total FROM dbo.Candidatos c WHERE {w}", p))
    k = sgo.fila(f"""
        SELECT COUNT(DISTINCT e.CandidatoId) AS candidatos_entrevistados, AVG({_CALIF}) AS calificacion_promedio,
               COUNT(*) AS total_entrevistas
        FROM dbo.Entrevistas e INNER JOIN dbo.Candidatos c ON e.CandidatoId = c.CandidatoId WHERE {w}""", p)
    case_r = "CASE " + " ".join(f"WHEN cnt {c} THEN '{e}'" for e, c in _RANGOS_ENT[:-1]) + " ELSE 'Más de 10' END"
    rangos = _orden(sgo.filas(f"""
        SELECT {case_r} AS label, COUNT(*) AS value
        FROM (SELECT c.CandidatoId, COUNT(e.EntrevistaId) AS cnt FROM dbo.Candidatos c
              LEFT JOIN dbo.Entrevistas e ON c.CandidatoId = e.CandidatoId WHERE {w} GROUP BY c.CandidatoId) x
        GROUP BY {case_r}""", p), [e for e, _ in _RANGOS_ENT])
    case_c = "CASE " + " ".join(f"WHEN {_CALIF} >= {mn} THEN '{e}'" for e, mn, _ in _RANGOS_CALIF[:-1]) + " ELSE 'Muy bajo (0-2)' END"
    califs = _orden(sgo.filas(f"""
        SELECT {case_c} AS label, COUNT(*) AS value FROM dbo.Entrevistas e INNER JOIN dbo.Candidatos c ON e.CandidatoId = c.CandidatoId
        WHERE {w} GROUP BY {case_c}""", p), [e for e, _, _ in _RANGOS_CALIF][::-1])
    por_perfil = sgo.filas(f"""
        SELECT TOP 15 RTRIM(pc.PerfilCandidatoDescripcion) AS label, COUNT(DISTINCT c.CandidatoId) AS candidatos,
               COUNT(e.EntrevistaId) AS entrevistas, AVG({_CALIF}) AS calificacion_promedio
        FROM dbo.Candidatos c {JOIN_PERFIL} INNER JOIN dbo.Entrevistas e ON c.CandidatoId = e.CandidatoId
        WHERE {w} GROUP BY pc.PerfilCandidatoId, pc.PerfilCandidatoDescripcion HAVING COUNT(e.EntrevistaId) >= 5
        ORDER BY calificacion_promedio DESC""", p)
    top = sgo.filas(f"""
        SELECT TOP 20 {NOMBRE} AS label, RTRIM(pc.PerfilCandidatoDescripcion) AS perfil, COUNT(e.EntrevistaId) AS total_entrevistas,
               AVG({_CALIF}) AS calificacion_promedio
        FROM dbo.Candidatos c {JOIN_PERFIL} INNER JOIN dbo.Entrevistas e ON c.CandidatoId = e.CandidatoId
        WHERE {w} GROUP BY c.CandidatoId, c.CandidatoNombre, c.CandidatoApellido, pc.PerfilCandidatoDescripcion
        ORDER BY total_entrevistas DESC""", p)
    evolucion = sgo.filas(f"""
        SELECT YEAR(e.EntrevistaFecha) AS anio, COUNT(*) AS cantidad_entrevistas, COUNT(DISTINCT e.CandidatoId) AS candidatos_unicos
        FROM dbo.Entrevistas e INNER JOIN dbo.Candidatos c ON e.CandidatoId = c.CandidatoId
        WHERE {w} AND e.EntrevistaFecha IS NOT NULL GROUP BY YEAR(e.EntrevistaFecha)
        HAVING YEAR(e.EntrevistaFecha) >= YEAR(GETDATE()) - 5 ORDER BY anio""", p)

    entrevistados = num(k.get("candidatos_entrevistados"))
    secciones = [
        seccion("Distribución por cantidad de entrevistas", [lider(rangos, "label", "value", "candidatos")],
                g.columnas(etiquetas(rangos), {"Candidatos": valores(rangos, "value")}, rotar=0),
                explicacion="Candidatos según cuántas entrevistas tuvieron en Manpower.", detalle="rango",
                ayuda_detalle="Hacé clic en un rango para ver esos candidatos."),
        seccion("Distribución de calificaciones", [lider(califs, "label", "value", "entrevistas")],
                g.columnas(etiquetas(califs), {"Entrevistas": valores(califs, "value")}, rotar=0, colores=[g.SERIES[2]]),
                explicacion="Entrevistas según su calificación total (formación + experiencia, de 2 a 10).", detalle="calificacion",
                ayuda_detalle="Hacé clic en un rango para ver los candidatos con ese promedio."),
        seccion("Calificación promedio por perfil", [extremos(por_perfil, "label", "calificacion_promedio", decimal, "mejor", "peor")],
                g.ranking(etiquetas(por_perfil), valores(por_perfil, "calificacion_promedio"), "Calificación", g.SERIES[1]),
                alto=g.alto_ranking(len(por_perfil)),
                explicacion="Calificación promedio de las entrevistas de cada perfil (5 entrevistas o más).", detalle="perfil",
                ayuda_detalle="Hacé clic en un perfil para ver sus candidatos."),
        seccion("Evolución de las entrevistas (últimos 5 años)", [],
                g.columnas([str(int(num(r["anio"]))) for r in evolucion], {"Entrevistas": valores(evolucion, "cantidad_entrevistas"),
                                                                          "Candidatos únicos": valores(evolucion, "candidatos_unicos")}, rotar=0),
                explicacion="Entrevistas y candidatos distintos entrevistados por año."),
        seccion("Top 20 candidatos más entrevistados", [],
                tabla=tabla("Más entrevistados", ["Candidato", "Perfil", "Entrevistas", "Calificación promedio"],
                            [[r["label"], r["perfil"], entero(r["total_entrevistas"]), decimal(r["calificacion_promedio"])] for r in top]),
                explicacion="Candidatos con más entrevistas registradas."),
    ]
    return {
        "kpis": [
            kpi("Total candidatos", entero(total_c)),
            kpi("Con entrevistas", entero(entrevistados), pct(proporcion(entrevistados, total_c))),
            kpi("Total entrevistas", entero(k.get("total_entrevistas"))),
            kpi("Calificación promedio", decimal(k.get("calificacion_promedio")), "de 2 a 10"),
            kpi("Entrevistas por candidato", decimal(proporcion(k.get("total_entrevistas"), entrevistados) / 100, 1), "promedio"),
        ],
        "conclusiones": [
            f"{pct(proporcion(entrevistados, total_c))} de los candidatos tuvo al menos una entrevista.",
            f"La calificación promedio es {decimal(k.get('calificacion_promedio'))} sobre 10.",
            extremos(por_perfil, "label", "calificacion_promedio", decimal, "perfil mejor calificado", "peor"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué perfiles obtienen mejores calificaciones?", "¿Cuántos candidatos nunca fueron entrevistados?"],
        "contexto_ia": {"rangos": rangos, "calificaciones": califs, "por_perfil": por_perfil},
    }


@catalogo.detalle("experiencia")
def detalle_experiencia(clave, valor, serie, periodo, filtros):
    w, p = where(filtros)
    if clave == "rango":
        condicion = f"{_N_ENT} " + next((c for e, c in _RANGOS_ENT if e == valor), "= -1")
        filas = sgo.filas(f"""
            SELECT TOP 500 c.CandidatoId, {NOMBRE} AS candidato, RTRIM(pc.PerfilCandidatoDescripcion) AS perfil, {_N_ENT} AS entrevistas,
                   (SELECT AVG(CAST(ez.EntrevistaPuntajeFormacion AS FLOAT) + CAST(ez.EntrevistaPuntajeExperiencia AS FLOAT))
                    FROM dbo.Entrevistas ez WHERE ez.CandidatoId = c.CandidatoId) AS calificacion
            FROM dbo.Candidatos c LEFT JOIN dbo.PerfilesCandidatos pc ON c.PerfilCandidatoId = pc.PerfilCandidatoId
            WHERE {w} AND {condicion} ORDER BY c.CandidatoApellido, c.CandidatoNombre""", p)
    else:
        having, extra, params = "", "", list(p)
        if clave == "calificacion":
            mn, mx = next(((a, b) for e, a, b in _RANGOS_CALIF if e == valor), (-1, -2))
            having = f"HAVING AVG({_CALIF}) >= %s AND AVG({_CALIF}) <= %s"
        else:
            extra = "AND RTRIM(pc.PerfilCandidatoDescripcion) = %s"
            params.append(valor)
        filas = sgo.filas(f"""
            SELECT TOP 500 c.CandidatoId, {NOMBRE} AS candidato, RTRIM(pc.PerfilCandidatoDescripcion) AS perfil,
                   COUNT(e.EntrevistaId) AS entrevistas, AVG({_CALIF}) AS calificacion
            FROM dbo.Candidatos c {JOIN_PERFIL} INNER JOIN dbo.Entrevistas e ON c.CandidatoId = e.CandidatoId
            WHERE {w} {extra}
            GROUP BY c.CandidatoId, c.CandidatoNombre, c.CandidatoApellido, pc.PerfilCandidatoDescripcion
            {having} ORDER BY calificacion DESC""", params + ([mn, mx] if clave == "calificacion" else []))
    return respuesta_detalle(f"Candidatos · {valor}", COLUMNAS_EXP, filas)


# ==========================================================================
# 6. Calidad y completitud de datos (can_dat)
# ==========================================================================
_TIENE_EMAIL = "c.CandidatoEmail IS NOT NULL AND RTRIM(c.CandidatoEmail) != ''"
_TIENE_CEL = "c.CandidatoCelular IS NOT NULL AND RTRIM(c.CandidatoCelular) != ''"
_SIN_EMAIL = "(c.CandidatoEmail IS NULL OR RTRIM(c.CandidatoEmail) = '')"
_SIN_CEL = "(c.CandidatoCelular IS NULL OR RTRIM(c.CandidatoCelular) = '')"
CAMPOS_COMPLETITUD = [
    ("Email", _TIENE_EMAIL, _SIN_EMAIL),
    ("Celular", _TIENE_CEL, _SIN_CEL),
    ("Teléfono", "c.CandidatoTelefono IS NOT NULL AND RTRIM(c.CandidatoTelefono) != ''",
     "(c.CandidatoTelefono IS NULL OR RTRIM(c.CandidatoTelefono) = '')"),
    ("Salario pretendido", "c.CandidatoSalarioPretendido > 0", "(c.CandidatoSalarioPretendido = 0 OR c.CandidatoSalarioPretendido IS NULL)"),
    ("Salario actual", "c.CandidatoSalarioActual > 0", "(c.CandidatoSalarioActual = 0 OR c.CandidatoSalarioActual IS NULL)"),
    ("Dirección", "c.CandidatoDireccion IS NOT NULL AND RTRIM(c.CandidatoDireccion) != ''",
     "(c.CandidatoDireccion IS NULL OR RTRIM(c.CandidatoDireccion) = '')"),
    ("Localidad", "c.CandidatoLocalidadId IS NOT NULL", "c.CandidatoLocalidadId IS NULL"),
    ("Departamento", "c.CandidatoDepartamentoId IS NOT NULL", "c.CandidatoDepartamentoId IS NULL"),
    ("Nacionalidad", "c.CandidatoNacionalidadId IS NOT NULL", "c.CandidatoNacionalidadId IS NULL"),
    ("Nivel educativo", "c.NivelEducativoId IS NOT NULL", "c.NivelEducativoId IS NULL"),
]
_RANGOS_SALARIO = [("No especificado", "c.CandidatoSalarioPretendido = 0 OR c.CandidatoSalarioPretendido IS NULL"),
                   ("Menos de $20 mil", "c.CandidatoSalarioPretendido < 20000"), ("$20 a $40 mil", "c.CandidatoSalarioPretendido < 40000"),
                   ("$40 a $60 mil", "c.CandidatoSalarioPretendido < 60000"), ("$60 a $80 mil", "c.CandidatoSalarioPretendido < 80000"),
                   ("Más de $80 mil", "1=1")]
COLUMNAS_CONTACTO = ["Candidato Id", "Candidato", "Perfil", "Email", "Celular", "Teléfono", "Salario pretendido"]


def _candidatos_contacto(filtros, condicion, params=None, joins="", extra="", columnas=None):
    w, p = where(filtros)
    return sgo.filas(f"""
        SELECT TOP 500 c.CandidatoId, {NOMBRE} AS candidato, RTRIM(pc.PerfilCandidatoDescripcion) AS perfil,
               RTRIM(c.CandidatoEmail) AS email, RTRIM(c.CandidatoCelular) AS celular, RTRIM(c.CandidatoTelefono) AS telefono,
               c.CandidatoSalarioPretendido AS salario{extra}
        FROM dbo.Candidatos c LEFT JOIN dbo.PerfilesCandidatos pc ON c.PerfilCandidatoId = pc.PerfilCandidatoId {joins}
        WHERE {w} AND ({condicion}) ORDER BY c.CandidatoApellido, c.CandidatoNombre""", p + list(params or []))


@catalogo.registrar(
    "calidad-datos", "Calidad y completitud de datos",
    "Qué datos faltan en las fichas de los candidatos (contacto, salario, ubicación) y en qué perfiles y departamentos.",
    usa_periodo=False, icono="bi-clipboard-data", filtros=[s.F_PERFIL, s.F_PAIS, s.F_DEPTO],
)
def calidad_datos(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_candidatos, COUNT(CASE WHEN {_TIENE_EMAIL} THEN 1 END) AS con_email,
               COUNT(CASE WHEN {_TIENE_CEL} THEN 1 END) AS con_celular, COUNT(CASE WHEN c.CandidatoSalarioPretendido > 0 THEN 1 END) AS con_salario,
               COUNT(CASE WHEN {_SIN_EMAIL} AND {_SIN_CEL} THEN 1 END) AS sin_contacto,
               COUNT(CASE WHEN {_TIENE_EMAIL} AND {_TIENE_CEL} AND c.CandidatoSalarioPretendido > 0 AND c.CandidatoLocalidadId IS NOT NULL
                          THEN 1 END) AS datos_completos
        FROM dbo.Candidatos c WHERE {w}""", p)
    campos_sql = ", ".join(f"COUNT(CASE WHEN {tiene} THEN 1 END) AS [{nombre}]" for nombre, tiene, _ in CAMPOS_COMPLETITUD)
    fila_campos = sgo.fila(f"SELECT {campos_sql} FROM dbo.Candidatos c WHERE {w}", p)
    total_c = num(k.get("total_candidatos"))
    campos = sorted(({"label": n, "value": round(proporcion(fila_campos.get(n), total_c), 1)} for n, _, _ in CAMPOS_COMPLETITUD),
                    key=lambda r: r["value"])
    matriz = sgo.filas(f"""
        SELECT CASE WHEN {_TIENE_EMAIL} THEN 'Con email' ELSE 'Sin email' END AS email,
               CASE WHEN {_TIENE_CEL} THEN 'Con celular' ELSE 'Sin celular' END AS celular, COUNT(*) AS cantidad
        FROM dbo.Candidatos c WHERE {w}
        GROUP BY CASE WHEN {_TIENE_EMAIL} THEN 'Con email' ELSE 'Sin email' END, CASE WHEN {_TIENE_CEL} THEN 'Con celular' ELSE 'Sin celular' END""", p)

    def completitud_por(join, desc, id_col, id_c):
        return sgo.filas(f"""
            SELECT TOP 15 RTRIM(x.{desc}) AS label, COUNT(*) AS total,
                   ROUND(AVG(CASE WHEN {_TIENE_EMAIL} THEN 1.0 ELSE 0 END) * 100, 1) AS pct_email,
                   ROUND(AVG(CASE WHEN {_TIENE_CEL} THEN 1.0 ELSE 0 END) * 100, 1) AS pct_celular,
                   ROUND(AVG(CASE WHEN c.CandidatoSalarioPretendido > 0 THEN 1.0 ELSE 0 END) * 100, 1) AS pct_salario,
                   ROUND(AVG(CASE WHEN {_TIENE_EMAIL} AND {_TIENE_CEL} AND c.CandidatoSalarioPretendido > 0 THEN 1.0 ELSE 0 END) * 100, 1) AS pct_completo
            FROM dbo.Candidatos c INNER JOIN dbo.{join} x ON c.{id_c} = x.{id_col}
            WHERE {w} GROUP BY x.{id_col}, x.{desc} ORDER BY total DESC""", p)

    por_perfil = completitud_por("PerfilesCandidatos", "PerfilCandidatoDescripcion", "PerfilCandidatoId", "PerfilCandidatoId")
    por_depto = completitud_por("Departamentos", "DepartamentoNombre", "DepartamentoId", "CandidatoDepartamentoId")
    case_s = "CASE " + " ".join(f"WHEN {c} THEN '{e}'" for e, c in _RANGOS_SALARIO[:-1]) + f" ELSE '{_RANGOS_SALARIO[-1][0]}' END"
    salarios = _orden(sgo.filas(f"SELECT {case_s} AS label, COUNT(*) AS value FROM dbo.Candidatos c WHERE {w} GROUP BY {case_s}", p),
                      [e for e, _ in _RANGOS_SALARIO])

    def celda(e, cel):
        return next((num(r["cantidad"]) for r in matriz if r["email"] == e and r["celular"] == cel), 0)

    secciones = [
        seccion("Completitud por campo", [f"El campo más incompleto es {campos[0]['label']} ({pct(campos[0]['value'])} completo)." if campos else ""],
                g.ranking(etiquetas(campos), valores(campos, "value"), "% completo", formato="fmt:pct"), alto=g.alto_ranking(len(campos)),
                explicacion="Parte de los candidatos que tiene cargado cada dato, del menos al más completo.", detalle="campo",
                ayuda_detalle="Hacé clic en un campo para ver los candidatos que no lo tienen."),
        seccion("Matriz email / celular", [f"{entero(celda('Sin email', 'Sin celular'))} candidatos no tienen ni email ni celular."],
                g.columnas(["Con celular", "Sin celular"], {"Con email": [celda("Con email", "Con celular"), celda("Con email", "Sin celular")],
                                                            "Sin email": [celda("Sin email", "Con celular"), celda("Sin email", "Sin celular")]},
                           rotar=0, colores=[g.SERIES[0], g.NEGATIVO]),
                explicacion="Combinaciones de email y celular: lo ideal es tener los dos.", detalle="matriz",
                ayuda_detalle="Hacé clic en una barra para ver esos candidatos."),
        seccion("Completitud por perfil (top 15 por cantidad)", [extremos(por_perfil, "label", "pct_completo", pct, "más completo", "menos")],
                g.ranking(etiquetas(por_perfil), valores(por_perfil, "pct_completo"), "% con datos completos", g.SERIES[2], formato="fmt:pct"),
                alto=g.alto_ranking(len(por_perfil)),
                explicacion="Parte de los candidatos de cada perfil con email, celular y salario pretendido.", detalle="perfil",
                ayuda_detalle="Hacé clic en un perfil para ver sus candidatos incompletos.",
                tabla=tabla("Por perfil", ["Perfil", "Candidatos", "% email", "% celular", "% salario", "% completo"],
                            [[r["label"], entero(r["total"]), pct(r["pct_email"]), pct(r["pct_celular"]), pct(r["pct_salario"]),
                              pct(r["pct_completo"])] for r in por_perfil])),
        seccion("Rangos salariales pretendidos", [lider(salarios, "label", "value", "candidatos")],
                g.columnas(etiquetas(salarios), {"Candidatos": valores(salarios, "value")}, rotar=0, colores=[g.SERIES[1]]),
                explicacion="Salario que pretende el candidato, en rangos.", detalle="salario",
                ayuda_detalle="Hacé clic en un rango para ver esos candidatos."),
        seccion("Completitud por departamento (top 15)", [extremos(por_depto, "label", "pct_completo", pct, "más completo", "menos")],
                g.ranking(etiquetas(por_depto), valores(por_depto, "pct_completo"), "% con datos completos", g.SERIES[3], formato="fmt:pct"),
                alto=g.alto_ranking(len(por_depto)),
                explicacion="Parte de los candidatos de cada departamento con email, celular y salario pretendido.", detalle="departamento",
                ayuda_detalle="Hacé clic en un departamento para ver sus candidatos incompletos."),
    ]
    return {
        "kpis": [
            kpi("Total candidatos", entero(total_c)),
            kpi("Con email", entero(k.get("con_email")), pct(proporcion(k.get("con_email"), total_c))),
            kpi("Con celular", entero(k.get("con_celular")), pct(proporcion(k.get("con_celular"), total_c))),
            kpi("Con salario pretendido", entero(k.get("con_salario")), pct(proporcion(k.get("con_salario"), total_c))),
            kpi("Datos completos", entero(k.get("datos_completos")), pct(proporcion(k.get("datos_completos"), total_c)),
                "Email, celular, salario pretendido y localidad."),
            kpi("Sin contacto", entero(k.get("sin_contacto")), "ni email ni celular", alerta=num(k.get("sin_contacto")) > 0),
        ],
        "conclusiones": [
            f"{pct(proporcion(k.get('datos_completos'), total_c))} de las fichas está completa.",
            f"{entero(k.get('sin_contacto'))} candidatos no tienen forma de contacto.",
            f"El dato que más falta es {campos[0]['label']}." if campos else "",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué datos faltan más?", "¿Cuántos candidatos no tienen contacto?"],
        "contexto_ia": {"kpis": k, "campos": campos, "por_perfil": por_perfil},
    }


@catalogo.detalle("calidad-datos")
def detalle_calidad_datos(clave, valor, serie, periodo, filtros):
    incompleto = f"NOT ({_TIENE_EMAIL} AND {_TIENE_CEL} AND c.CandidatoSalarioPretendido > 0)"
    params, joins = [], ""
    if clave == "campo":
        condicion = next((sin for n, _, sin in CAMPOS_COMPLETITUD if n == valor), "1=0")
    elif clave == "matriz":
        condicion = f"{_TIENE_EMAIL if serie == 'Con email' else _SIN_EMAIL} AND {_TIENE_CEL if valor == 'Con celular' else _SIN_CEL}"
    elif clave == "salario":
        partes, previas = [], []
        for e, c in _RANGOS_SALARIO:
            if e == valor:
                partes = [f"({c})"] + [f"NOT ({x})" for x in previas]
                break
            previas.append(c)
        condicion = " AND ".join(partes) or "1=0"
    elif clave == "perfil":
        condicion, params = f"RTRIM(pc.PerfilCandidatoDescripcion) = %s AND {incompleto}", [valor]
    else:
        condicion, params = f"RTRIM(d.DepartamentoNombre) = %s AND {incompleto}", [valor]
        joins = "LEFT JOIN dbo.Departamentos d ON c.CandidatoDepartamentoId = d.DepartamentoId"
    titulo = f"Candidatos · {valor}" + (f" · {serie}" if clave == "matriz" else "") + (" · sin el dato" if clave == "campo" else "")
    return respuesta_detalle(titulo, COLUMNAS_CONTACTO, _candidatos_contacto(filtros, condicion, params, joins))


# ==========================================================================
# 7. Problemas y errores de datos (can_err)
# ==========================================================================
PROBLEMAS = [
    ("Sin contacto", f"{_SIN_EMAIL} AND {_SIN_CEL}", "crítico"),
    ("Email inválido", f"{_TIENE_EMAIL} AND CHARINDEX('@', RTRIM(c.CandidatoEmail)) = 0", "inválido"),
    ("Celular inválido", f"{_TIENE_CEL} AND LEN(RTRIM(c.CandidatoCelular)) < 8", "inválido"),
    ("Libreta sin categoría", "c.CandidatoLibretaConducir = 'S' AND c.CategoriaLibretaConducirId IS NULL", "inconsistencia"),
    ("Categoría sin libreta", "(c.CandidatoLibretaConducir = 'N' OR c.CandidatoLibretaConducir IS NULL) AND c.CategoriaLibretaConducirId IS NOT NULL",
     "inconsistencia"),
    ("Carné de salud vencido", "c.CandidatoCarneSalud = 'S' AND c.CandidatoVencimientoCarneSalud < GETDATE() "
                               "AND c.CandidatoVencimientoCarneSalud > '1900-01-01'", "inconsistencia"),
    ("Edad inválida", f"c.CandidatoFechaNacimiento > '1900-01-01' AND ({EDAD} < 16 OR {EDAD} > 80)", "inválido"),
    ("Fecha de nacimiento futura", "c.CandidatoFechaNacimiento > GETDATE()", "inválido"),
]
_DUP_DOC = "c.CandidatoNroDocumento IN (SELECT c2.CandidatoNroDocumento FROM dbo.Candidatos c2 WHERE {w2} GROUP BY c2.CandidatoNroDocumento HAVING COUNT(*) > 1)"
_DUP_EMAIL = (f"{_TIENE_EMAIL} AND RTRIM(c.CandidatoEmail) IN (SELECT RTRIM(c2.CandidatoEmail) FROM dbo.Candidatos c2 WHERE {{w2}} "
              "AND c2.CandidatoEmail IS NOT NULL AND RTRIM(c2.CandidatoEmail) != '' GROUP BY RTRIM(c2.CandidatoEmail) HAVING COUNT(*) > 1)")


@catalogo.registrar(
    "problemas-datos", "Problemas y errores de datos",
    "Fichas con errores: sin contacto, emails o celulares inválidos, inconsistencias de libreta y carné, edades imposibles y duplicados.",
    usa_periodo=False, icono="bi-bug", filtros=[s.F_PERFIL, s.F_PAIS],
)
def problemas_datos(periodo, filtros):
    w, p = where(filtros)
    w2, p2 = where(filtros, "c2")
    sumas = ", ".join(f"SUM(CASE WHEN {cond} THEN 1 ELSE 0 END) AS [{nombre}]" for nombre, cond, _ in PROBLEMAS)
    k = sgo.fila(f"SELECT COUNT(*) AS total_candidatos, {sumas} FROM dbo.Candidatos c WHERE {w}", p)
    dup_doc = num(sgo.valor(f"""SELECT COUNT(*) AS duplicados FROM (SELECT c.CandidatoNroDocumento FROM dbo.Candidatos c WHERE {w}
                                 GROUP BY c.CandidatoNroDocumento HAVING COUNT(*) > 1) x""", p))
    dup_email = num(sgo.valor(f"""SELECT COUNT(*) AS duplicados FROM (SELECT RTRIM(c.CandidatoEmail) AS email FROM dbo.Candidatos c
                                   WHERE {w} AND {_TIENE_EMAIL} GROUP BY RTRIM(c.CandidatoEmail) HAVING COUNT(*) > 1) x""", p))
    por_perfil = sgo.filas(f"""
        SELECT TOP 15 RTRIM(pc.PerfilCandidatoDescripcion) AS label, COUNT(*) AS total_candidatos,
               SUM(CASE WHEN {PROBLEMAS[0][1]} THEN 1 ELSE 0 END) AS sin_contacto,
               SUM(CASE WHEN {PROBLEMAS[1][1]} THEN 1 ELSE 0 END) AS email_invalido,
               SUM(CASE WHEN {PROBLEMAS[3][1]} THEN 1 ELSE 0 END) AS libreta_sin_categoria
        FROM dbo.Candidatos c {JOIN_PERFIL} WHERE {w}
        GROUP BY pc.PerfilCandidatoId, pc.PerfilCandidatoDescripcion ORDER BY total_candidatos DESC""", p)
    faltantes_sql = ", ".join(f"SUM(CASE WHEN {sin} THEN 1 ELSE 0 END) AS [{n}]" for n, _, sin in CAMPOS_COMPLETITUD
                              if n in ("Email", "Celular", "Dirección", "Departamento", "Localidad"))
    falt = sgo.fila(f"SELECT {faltantes_sql} FROM dbo.Candidatos c WHERE {w}", p)

    total_c = num(k.get("total_candidatos"))
    dist = [{"label": n, "value": num(k.get(n)), "tipo": t} for n, _, t in PROBLEMAS]
    dist += [{"label": "Documento duplicado", "value": dup_doc, "tipo": "crítico"},
             {"label": "Email duplicado", "value": dup_email, "tipo": "crítico"}]
    criticos = sum(r["value"] for r in dist if r["tipo"] == "crítico")
    inconsist = sum(r["value"] for r in dist if r["tipo"] == "inconsistencia")
    invalidos = sum(r["value"] for r in dist if r["tipo"] == "inválido")
    colores_tipo = {"crítico": g.NEGATIVO, "inconsistencia": g.ESTADO["serio"], "inválido": g.ESTADO["atencion"]}
    dist_orden = sorted(dist, key=lambda r: -r["value"])
    grafico = g.ranking(etiquetas(dist_orden), valores(dist_orden, "value"), "Candidatos")
    grafico["series"][0]["data"] = [{"value": r["value"], "itemStyle": {"color": colores_tipo[r["tipo"]]}} for r in dist_orden]
    faltantes = sorted(({"label": f"Sin {n.lower()}", "value": num(v)} for n, v in falt.items()), key=lambda r: -r["value"])
    secciones = [
        seccion("Distribución de problemas", [lider(dist_orden, "label", "value", "casos", "los problemas detectados")], grafico,
                alto=g.alto_ranking(len(dist_orden)),
                explicacion="Rojo: errores críticos (sin contacto, duplicados). Naranja: inconsistencias (libreta, carné). "
                            "Amarillo: datos inválidos (email sin @, celular corto, edades imposibles). Los duplicados cuentan "
                            "documentos o emails repetidos, no candidatos.",
                detalle="problema", ayuda_detalle="Hacé clic en un problema para ver los candidatos a corregir."),
        seccion("Datos faltantes más comunes", [lider(faltantes, "label", "value", "candidatos")],
                g.ranking(etiquetas(faltantes), valores(faltantes, "value"), "Candidatos", g.SERIES[1]), alto=g.alto_ranking(len(faltantes), 200),
                explicacion="Candidatos sin cada dato básico."),
        seccion("Problemas por perfil (top 15)", [],
                g.columnas(etiquetas(por_perfil), {"Sin contacto": valores(por_perfil, "sin_contacto"),
                                                   "Email inválido": valores(por_perfil, "email_invalido"),
                                                   "Libreta sin categoría": valores(por_perfil, "libreta_sin_categoria")}, apiladas=True,
                           colores=[g.NEGATIVO, g.ESTADO["atencion"], g.ESTADO["serio"]]), alto=360,
                explicacion="Los tres problemas más frecuentes en los 15 perfiles con más candidatos.", detalle="perfil",
                ayuda_detalle="Hacé clic en un tramo para ver esos candidatos."),
    ]
    return {
        "kpis": [
            kpi("Total candidatos", entero(total_c)),
            kpi("Errores críticos", entero(criticos), "sin contacto y duplicados", alerta=criticos > 0),
            kpi("Inconsistencias", entero(inconsist), "libreta y carné"),
            kpi("Datos inválidos", entero(invalidos), "email, celular y edad"),
            kpi("Total de problemas", entero(criticos + inconsist + invalidos)),
        ],
        "conclusiones": [
            f"Se detectaron {entero(criticos + inconsist + invalidos)} problemas en {entero(total_c)} fichas.",
            lider(dist_orden, "label", "value", "casos", "los problemas"),
            f"{entero(dup_doc)} documentos aparecen repetidos." if dup_doc else "",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué errores de datos hay que corregir primero?", "¿Cuántos documentos están duplicados?"],
        "contexto_ia": {"problemas": dist, "faltantes": faltantes},
    }


@catalogo.detalle("problemas-datos")
def detalle_problemas_datos(clave, valor, serie, periodo, filtros):
    w2, p2 = where(filtros, "c2")
    params = []
    if clave == "perfil":
        cond_serie = {"Sin contacto": PROBLEMAS[0][1], "Email inválido": PROBLEMAS[1][1], "Libreta sin categoría": PROBLEMAS[3][1]}
        condicion, params = f"RTRIM(pc.PerfilCandidatoDescripcion) = %s AND ({cond_serie.get(serie, '1=1')})", [valor]
    elif valor == "Documento duplicado":
        condicion, params = _DUP_DOC.format(w2=w2), p2
    elif valor == "Email duplicado":
        condicion, params = _DUP_EMAIL.format(w2=w2), p2
    else:
        condicion = next((c for n, c, _ in PROBLEMAS if n == valor), "1=0")
    filas = _candidatos_contacto(filtros, condicion, params)
    return respuesta_detalle(f"Candidatos · {valor}" + (f" · {serie}" if clave == "perfil" else ""), COLUMNAS_CONTACTO, filas)
