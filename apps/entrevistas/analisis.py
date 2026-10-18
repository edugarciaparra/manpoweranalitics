"""
Análisis del módulo Entrevistas: las 8 pantallas de entrevistas del SGO
(ent_res, ent_per, ent_cal, ent_can, ent_pub, ent_ped, ent_cua, ent_psi) con el
mismo SQL, filtros y clasificación de textos, y los registros en el modal.
"""
from collections import defaultdict

from apps.core import graficos as g
from apps.core import sgo
from apps.core.analisis import Catalogo, seccion
from apps.core.pantalla import (
    concentracion, decimal, detalle as respuesta_detalle, entero, etiquetas, extremos, kpi, lider, pct,
    proporcion, tabla, total, valores,
)
from apps.core.sgo import num

from . import services as s
from .services import (
    AVG_E, AVG_F, AVG_T, CONTRATADOS, JOIN_ASIGNADO, JOIN_CONTRATO, JOIN_PSI, PCT_ASIGNADO, PCT_CONTRATO, PSICOLOGO,
    PUNTAJE_E, PUNTAJE_F, TOTAL, ASIGNADOS, where,
)

catalogo = Catalogo()

FILTROS_RESUMEN = [s.F_PSICOLOGO, s.F_TIPO, s.F_SITUACION, s.F_DESDE, s.F_HASTA]
_ESCALA = "Los puntajes de formación y experiencia van de 1 a 5 cada uno (total de 2 a 10)."


def _mes(r):
    return r.get("label") or f"{int(num(r.get('anio')))}-{int(num(r.get('mes'))):02d}"


def _bins(expresion, cortes):
    """CASE ... END a partir de [(etiqueta, condición), ...] usando la expresión dada."""
    partes = " ".join(f"WHEN {c.format(x=expresion)} THEN '{e}'" for e, c in cortes[:-1])
    return f"CASE {partes} ELSE '{cortes[-1][0]}' END"


# ==========================================================================
# 1. Resumen general (ent_res)
# ==========================================================================
_CORTES_RESUMEN = [("Bajo (0-9)", "{x} < 10"), ("Medio (10-14)", "{x} BETWEEN 10 AND 14"),
                   ("Alto (15-19)", "{x} BETWEEN 15 AND 19"), ("Excelente (20+)", "{x} >= 20")]


@catalogo.registrar(
    "resumen", "Resumen general",
    "Cuántas entrevistas se hacen, de qué canales vienen, quién las hace, qué puntajes tienen y si están ligadas a pedidos.",
    usa_periodo=False, icono="bi-speedometer2", filtros=FILTROS_RESUMEN,
)
def resumen(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_entrevistas, COUNT(DISTINCT e.CandidatoId) AS candidatos_unicos,
               COUNT(CASE WHEN e.EntrevistaEsGrupal = 'S' THEN 1 END) AS entrevistas_grupales,
               COUNT(CASE WHEN e.EntrevistaEsGrupal = 'N' THEN 1 END) AS entrevistas_individuales,
               ROUND(AVG({PUNTAJE_F}), 2) AS avg_puntaje_formacion, ROUND(AVG({PUNTAJE_E}), 2) AS avg_puntaje_experiencia,
               COUNT(DISTINCT e.EntrevistaPsicologoId) AS total_psicologos
        FROM dbo.Entrevistas e WHERE {w}""", p)
    tendencia = sgo.filas(f"""
        SELECT YEAR(e.EntrevistaFecha) AS anio, MONTH(e.EntrevistaFecha) AS mes,
               CAST(YEAR(e.EntrevistaFecha) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(e.EntrevistaFecha) AS VARCHAR), 2) AS label,
               COUNT(*) AS total_entrevistas, COUNT(DISTINCT e.CandidatoId) AS candidatos_unicos
        FROM dbo.Entrevistas e WHERE {w} GROUP BY YEAR(e.EntrevistaFecha), MONTH(e.EntrevistaFecha) ORDER BY anio, mes""", p)
    canales = sgo.filas(f"""
        SELECT ISNULL(cp.CanalPublicacionDescripcion, 'Sin canal') AS label, COUNT(*) AS total_entrevistas,
               COUNT(DISTINCT e.CandidatoId) AS candidatos_unicos
        FROM dbo.Entrevistas e LEFT JOIN dbo.CanalesPublicacionAvisos cp ON e.EntrevistaCanalPublicacion = cp.CanalPublicacionId
        WHERE {w} GROUP BY cp.CanalPublicacionId, cp.CanalPublicacionDescripcion ORDER BY total_entrevistas DESC""", p)
    tipos = sgo.filas(f"""
        SELECT CASE WHEN e.EntrevistaEsGrupal = 'S' THEN 'Grupal' ELSE 'Individual' END AS label, COUNT(*) AS value
        FROM dbo.Entrevistas e WHERE {w} GROUP BY CASE WHEN e.EntrevistaEsGrupal = 'S' THEN 'Grupal' ELSE 'Individual' END
        ORDER BY value DESC""", p)
    psicologos = sgo.filas(f"""
        SELECT TOP 10 {PSICOLOGO} AS label, COUNT(*) AS total_entrevistas, COUNT(DISTINCT e.CandidatoId) AS candidatos_unicos,
               ROUND(AVG({PUNTAJE_F}), 2) AS avg_puntaje
        FROM dbo.Entrevistas e {JOIN_PSI} WHERE {w}
        GROUP BY p.PsicologoId, p.PsicologoNombre, p.PsicologoApellido ORDER BY total_entrevistas DESC""", p)
    situaciones = sgo.filas(f"""
        SELECT ISNULL(sl.SituacionLaboralNombre, 'Sin especificar') AS label, COUNT(*) AS value
        FROM dbo.Entrevistas e LEFT JOIN dbo.SituacionesLaborales sl ON e.SituacionLaboralId = sl.SituacionLaboralId
        WHERE {w} GROUP BY sl.SituacionLaboralId, sl.SituacionLaboralNombre ORDER BY value DESC""", p)
    bins = _bins(TOTAL, _CORTES_RESUMEN)
    puntajes = sgo.filas(f"""
        SELECT {bins} AS label, COUNT(*) AS value FROM dbo.Entrevistas e WHERE {w}
        GROUP BY {bins} ORDER BY MIN({TOTAL})""", p)
    vinculo = sgo.filas(f"""
        SELECT CASE WHEN e.EntrevistaPedidoId IS NOT NULL THEN 'Con pedido' ELSE 'Sin pedido' END AS label, COUNT(*) AS value
        FROM dbo.Entrevistas e WHERE {w}
        GROUP BY CASE WHEN e.EntrevistaPedidoId IS NOT NULL THEN 'Con pedido' ELSE 'Sin pedido' END ORDER BY value DESC""", p)

    pico = max(tendencia, key=lambda r: num(r["total_entrevistas"]), default=None)
    con_pedido = next((num(r["value"]) for r in vinculo if r["label"] == "Con pedido"), 0)
    secciones = [
        seccion(
            "Tendencia mensual de entrevistas",
            [f"El mes con más entrevistas fue {_mes(pico)} ({entero(pico['total_entrevistas'])})." if pico else ""],
            g.lineas([_mes(r) for r in tendencia], {"Entrevistas": valores(tendencia, "total_entrevistas"),
                                                    "Candidatos únicos": valores(tendencia, "candidatos_unicos")}, area=True),
            explicacion="Entrevistas por mes (EntrevistaFecha) y cuántos candidatos distintos se entrevistaron.",
            detalle="mes", ayuda_detalle="Hacé clic en un mes para ver sus entrevistas.",
        ),
        seccion(
            "Entrevistas por canal de publicación",
            [lider(canales, "label", "total_entrevistas", "entrevistas"), concentracion(canales, "total_entrevistas", 3, "entrevistas")],
            g.ranking(etiquetas(canales), valores(canales, "total_entrevistas"), "Entrevistas"),
            alto=g.alto_ranking(len(canales)),
            explicacion="Canal por el que llegó el candidato a la entrevista.",
            detalle="canal", ayuda_detalle="Hacé clic en un canal para ver sus entrevistas.",
        ),
        seccion(
            "Tipo de entrevista",
            [f"{pct(proporcion(k.get('entrevistas_grupales'), k.get('total_entrevistas')))} de las entrevistas fueron grupales."],
            g.torta([(r["label"], num(r["value"])) for r in tipos]),
            explicacion="Entrevistas individuales y grupales (EntrevistaEsGrupal).",
            detalle="tipo", ayuda_detalle="Hacé clic en una porción para ver esas entrevistas.",
        ),
        seccion(
            "Top 10 psicólogos por volumen",
            [lider(psicologos, "label", "total_entrevistas", "entrevistas", "el top 10")],
            g.ranking(etiquetas(psicologos), valores(psicologos, "total_entrevistas"), "Entrevistas", g.SERIES[1]),
            alto=g.alto_ranking(len(psicologos)),
            explicacion="Los 10 psicólogos que más entrevistas hicieron.",
            detalle="psicologo", ayuda_detalle="Hacé clic en un psicólogo para ver sus entrevistas.",
        ),
        seccion(
            "Distribución por situación laboral",
            [lider(situaciones, "label", "value", "entrevistas")],
            g.ranking(etiquetas(situaciones), valores(situaciones, "value"), "Entrevistas", g.SERIES[2]),
            alto=g.alto_ranking(len(situaciones), 200),
            explicacion="Situación laboral declarada por el candidato al momento de la entrevista.",
            detalle="situacion", ayuda_detalle="Hacé clic en una situación para ver esas entrevistas.",
        ),
        seccion(
            "Distribución de puntajes totales",
            [lider(puntajes, "label", "value", "entrevistas")],
            g.columnas(etiquetas(puntajes), {"Entrevistas": valores(puntajes, "value")}, rotar=0),
            explicacion="Suma de puntaje de formación y de experiencia, agrupada en los rangos del SGO.",
        ),
        seccion(
            "Vinculación con pedidos",
            [f"{pct(proporcion(con_pedido, total(vinculo, 'value')))} de las entrevistas está asociada a un pedido."],
            g.torta([(r["label"], num(r["value"])) for r in vinculo], colores=[g.SERIES[0], g.NEUTRO]),
            explicacion="Entrevistas que tienen un pedido asociado (EntrevistaPedidoId) y las que no.",
            detalle="vinculo", ayuda_detalle="Hacé clic en una porción para ver esas entrevistas.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total entrevistas", entero(k.get("total_entrevistas"))),
            kpi("Candidatos únicos", entero(k.get("candidatos_unicos"))),
            kpi("Entrevistas grupales", entero(k.get("entrevistas_grupales")),
                f"{entero(k.get('entrevistas_individuales'))} individuales"),
            kpi("Puntaje de formación", decimal(k.get("avg_puntaje_formacion")), "promedio", _ESCALA),
            kpi("Puntaje de experiencia", decimal(k.get("avg_puntaje_experiencia")), "promedio", _ESCALA),
            kpi("Psicólogos activos", entero(k.get("total_psicologos"))),
        ],
        "conclusiones": [
            f"Se hicieron {entero(k.get('total_entrevistas'))} entrevistas a {entero(k.get('candidatos_unicos'))} candidatos.",
            lider(canales, "label", "total_entrevistas", "entrevistas"),
            f"{pct(proporcion(con_pedido, total(vinculo, 'value')))} de las entrevistas está asociada a un pedido.",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué canal trae más candidatos?", "¿Cómo viene el volumen de entrevistas?"],
        "contexto_ia": {"kpis": k, "tendencia": tendencia, "canales": canales, "psicologos": psicologos,
                        "situaciones": situaciones, "puntajes": puntajes, "vinculo": vinculo},
    }


def _condicion_comun(clave, valor):
    """Condición SQL y parámetros para las claves de detalle que se repiten entre pantallas."""
    return {
        "mes": ("FORMAT(e.EntrevistaFecha, 'yyyy-MM') = %s", [valor]),
        "canal": ("ISNULL(cp.CanalPublicacionDescripcion, 'Sin canal') = %s", [valor]),
        "tipo": ("e.EntrevistaEsGrupal = %s", ["S" if valor == "Grupal" else "N"]),
        "psicologo": (f"{PSICOLOGO} = %s", [valor]),
        "situacion": ("ISNULL(sl.SituacionLaboralNombre, 'Sin especificar') = %s", [valor]),
        "vinculo": ("e.EntrevistaPedidoId IS NOT NULL" if valor == "Con pedido" else "e.EntrevistaPedidoId IS NULL", []),
    }.get(clave, ("1=0", []))


_JOINS_COMUNES = """LEFT JOIN dbo.CanalesPublicacionAvisos cp ON e.EntrevistaCanalPublicacion = cp.CanalPublicacionId
        LEFT JOIN dbo.SituacionesLaborales sl ON e.SituacionLaboralId = sl.SituacionLaboralId"""


@catalogo.detalle("resumen")
def detalle_resumen(clave, valor, serie, periodo, filtros):
    condicion, params = _condicion_comun(clave, valor)
    filas, columnas = s.entrevistas(filtros, condicion, params, joins=_JOINS_COMUNES)
    return respuesta_detalle(f"Entrevistas · {valor}", columnas, filas)


# ==========================================================================
# 2. Performance de psicólogos (ent_per)
# ==========================================================================
@catalogo.registrar(
    "psicologos", "Performance de psicólogos",
    "Volumen, puntajes, tipo de entrevista, conversión a contratación y consistencia de cada psicólogo.",
    usa_periodo=False, icono="bi-person-video2", filtros=[s.F_PSICOLOGO, s.F_DESDE, s.F_HASTA],
)
def psicologos(periodo, filtros):
    w, p = where(filtros)
    agrupa = "GROUP BY p.PsicologoId, p.PsicologoNombre, p.PsicologoApellido"
    k = sgo.fila(f"""
        SELECT COUNT(DISTINCT e.EntrevistaPsicologoId) AS total_psicologos, COUNT(*) AS total_entrevistas,
               ROUND(CAST(COUNT(*) AS FLOAT) / NULLIF(COUNT(DISTINCT e.EntrevistaPsicologoId), 0), 2) AS avg_entrevistas_por_psicologo,
               {AVG_F} AS avg_puntaje_formacion, {AVG_E} AS avg_puntaje_experiencia, {AVG_T} AS avg_puntaje_total
        FROM dbo.Entrevistas e WHERE {w}""", p)
    volumen = sgo.filas(f"""
        SELECT TOP 15 {PSICOLOGO} AS label, COUNT(*) AS total_entrevistas, COUNT(DISTINCT e.CandidatoId) AS candidatos_unicos,
               ROUND(CAST(COUNT(*) AS FLOAT) / NULLIF(DATEDIFF(DAY, MIN(e.EntrevistaFecha), MAX(e.EntrevistaFecha)), 0), 2) AS entrevistas_por_dia
        FROM dbo.Entrevistas e {JOIN_PSI} WHERE {w} {agrupa} ORDER BY total_entrevistas DESC""", p)
    puntajes = sgo.filas(f"""
        SELECT TOP 15 {PSICOLOGO} AS label, {AVG_F} AS avg_formacion, {AVG_E} AS avg_experiencia, {AVG_T} AS avg_total
        FROM dbo.Entrevistas e {JOIN_PSI} WHERE {w} {agrupa} HAVING COUNT(*) >= 5 ORDER BY avg_total DESC""", p)
    tendencia = sgo.filas(f"""
        SELECT YEAR(e.EntrevistaFecha) AS anio, MONTH(e.EntrevistaFecha) AS mes,
               CAST(YEAR(e.EntrevistaFecha) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(e.EntrevistaFecha) AS VARCHAR), 2) AS label,
               COUNT(*) AS total_entrevistas, COUNT(DISTINCT e.EntrevistaPsicologoId) AS psicologos_activos,
               ROUND(CAST(COUNT(*) AS FLOAT) / NULLIF(COUNT(DISTINCT e.EntrevistaPsicologoId), 0), 2) AS avg_por_psicologo
        FROM dbo.Entrevistas e WHERE {w} GROUP BY YEAR(e.EntrevistaFecha), MONTH(e.EntrevistaFecha) ORDER BY anio, mes""", p)
    tipo = sgo.filas(f"""
        SELECT TOP 10 {PSICOLOGO} AS label, COUNT(CASE WHEN e.EntrevistaEsGrupal = 'N' THEN 1 END) AS individuales,
               COUNT(CASE WHEN e.EntrevistaEsGrupal = 'S' THEN 1 END) AS grupales
        FROM dbo.Entrevistas e {JOIN_PSI} WHERE {w} {agrupa} ORDER BY COUNT(*) DESC""", p)
    conversion = sgo.filas(f"""
        SELECT TOP 10 {PSICOLOGO} AS label, COUNT(DISTINCT e.CandidatoId) AS candidatos_entrevistados,
               {CONTRATADOS} AS candidatos_contratados, {PCT_CONTRATO} AS pct_conversion
        FROM dbo.Entrevistas e {JOIN_PSI} {JOIN_CONTRATO} WHERE {w} {agrupa}
        HAVING COUNT(DISTINCT e.CandidatoId) >= 10 ORDER BY pct_conversion DESC""", p)
    variabilidad = sgo.filas(f"""
        SELECT TOP 10 {PSICOLOGO} AS label, COUNT(*) AS total_entrevistas, {AVG_T} AS avg_puntaje,
               ROUND(ISNULL(STDEV(CASE WHEN {TOTAL} > 0 THEN {TOTAL} END), 0), 2) AS desviacion_estandar,
               ROUND(MIN(CASE WHEN {TOTAL} > 0 THEN {TOTAL} END), 2) AS min_puntaje,
               ROUND(MAX(CASE WHEN {TOTAL} > 0 THEN {TOTAL} END), 2) AS max_puntaje
        FROM dbo.Entrevistas e {JOIN_PSI} WHERE {w} {agrupa} HAVING COUNT(*) >= 10
        ORDER BY ISNULL(STDEV(CASE WHEN {TOTAL} > 0 THEN {TOTAL} END), 0) ASC""", p)
    matriz = sgo.filas(f"""
        SELECT {PSICOLOGO} AS psicologo, COUNT(*) AS total_entrevistas, {AVG_T} AS avg_puntaje,
               {PCT_CONTRATO} AS pct_conversion
        FROM dbo.Entrevistas e {JOIN_PSI} {JOIN_CONTRATO} WHERE {w} {agrupa} HAVING COUNT(*) >= 10
        ORDER BY total_entrevistas DESC""", p)

    secciones = [
        seccion(
            "Tendencia mensual: entrevistas y psicólogos activos",
            [f"En el último mes hubo {entero(tendencia[-1]['psicologos_activos'])} psicólogos activos con "
             f"{decimal(tendencia[-1]['avg_por_psicologo'])} entrevistas cada uno." if tendencia else ""],
            g.lineas([_mes(r) for r in tendencia], {"Entrevistas por psicólogo": valores(tendencia, "avg_por_psicologo")}),
            explicacion="Entrevistas por mes divididas entre los psicólogos que entrevistaron ese mes. La tabla tiene "
                        "el total de entrevistas y de psicólogos activos.",
            tabla=tabla("Por mes", ["Mes", "Entrevistas", "Psicólogos activos", "Por psicólogo"],
                        [[_mes(r), entero(r["total_entrevistas"]), entero(r["psicologos_activos"]),
                          decimal(r["avg_por_psicologo"])] for r in tendencia[-12:]]),
        ),
        seccion(
            "Top 15 psicólogos por volumen",
            [lider(volumen, "label", "total_entrevistas", "entrevistas", "el top 15")],
            g.ranking(etiquetas(volumen), valores(volumen, "total_entrevistas"), "Entrevistas"), alto=g.alto_ranking(len(volumen)),
            explicacion="Psicólogos con más entrevistas en el período.",
            detalle="psicologo", ayuda_detalle="Hacé clic en un psicólogo para ver sus entrevistas.",
        ),
        seccion(
            "Top 15 psicólogos por puntajes",
            [extremos(puntajes, "label", "avg_total", decimal, "puntaje promedio más alto", "más bajo"), _ESCALA],
            g.columnas(etiquetas(puntajes), {"Formación": valores(puntajes, "avg_formacion"),
                                             "Experiencia": valores(puntajes, "avg_experiencia")}),
            alto=360,
            explicacion="Puntaje promedio de formación y de experiencia que pone cada psicólogo (con 5 entrevistas o más).",
            detalle="psicologo", ayuda_detalle="Hacé clic en un psicólogo para ver sus entrevistas.",
        ),
        seccion(
            "Top 10 por tipo de entrevista",
            [],
            g.columnas(etiquetas(tipo), {"Individuales": valores(tipo, "individuales"),
                                         "Grupales": valores(tipo, "grupales")}, apiladas=True),
            alto=360,
            explicacion="Entrevistas individuales y grupales de los 10 psicólogos con más entrevistas.",
            detalle="psicologo_tipo", ayuda_detalle="Hacé clic en un tramo para ver esas entrevistas.",
        ),
        seccion(
            "Top 10 por tasa de conversión",
            [extremos(conversion, "label", "pct_conversion", pct, "mejor conversión", "peor")],
            g.ranking(etiquetas(conversion), valores(conversion, "pct_conversion"), "% contratados", g.SERIES[2],
                      formato="fmt:pct"),
            alto=g.alto_ranking(len(conversion)),
            explicacion="Candidatos entrevistados que después ingresaron en una asignación ÷ candidatos entrevistados. "
                        "Solo psicólogos con 10 candidatos o más.",
            detalle="psicologo", ayuda_detalle="Hacé clic en un psicólogo para ver sus entrevistas.",
        ),
        seccion(
            "Consistencia de puntajes",
            ["Arriba, los psicólogos que califican de forma más pareja (menor desvío)."],
            tabla=tabla("Variabilidad del puntaje total", ["Psicólogo", "Entrevistas", "Promedio", "Desvío", "Mínimo", "Máximo"],
                        [[r["label"], entero(r["total_entrevistas"]), decimal(r["avg_puntaje"]), decimal(r["desviacion_estandar"]),
                          decimal(r["min_puntaje"]), decimal(r["max_puntaje"])] for r in variabilidad]),
            explicacion="Desvío estándar del puntaje total de cada psicólogo con 10 entrevistas o más.",
        ),
        seccion(
            "Matriz comparativa de psicólogos",
            [],
            tabla=tabla("Comparativa", ["Psicólogo", "Entrevistas", "Puntaje promedio", "% conversión"],
                        [[r["psicologo"], entero(r["total_entrevistas"]), decimal(r["avg_puntaje"]), pct(r["pct_conversion"])]
                         for r in matriz]),
            explicacion="Volumen, puntaje promedio y conversión de todos los psicólogos con 10 entrevistas o más.",
        ),
    ]
    return {
        "kpis": [
            kpi("Psicólogos activos", entero(k.get("total_psicologos"))),
            kpi("Entrevistas por psicólogo", decimal(k.get("avg_entrevistas_por_psicologo")), "promedio"),
            kpi("Puntaje de formación", decimal(k.get("avg_puntaje_formacion")), "promedio", _ESCALA),
            kpi("Puntaje de experiencia", decimal(k.get("avg_puntaje_experiencia")), "promedio", _ESCALA),
            kpi("Puntaje total", decimal(k.get("avg_puntaje_total")), "promedio", _ESCALA),
        ],
        "conclusiones": [
            f"{entero(k.get('total_psicologos'))} psicólogos hicieron {entero(k.get('total_entrevistas'))} entrevistas "
            f"({decimal(k.get('avg_entrevistas_por_psicologo'))} cada uno).",
            lider(volumen, "label", "total_entrevistas", "entrevistas", "el top 15"),
            extremos(conversion, "label", "pct_conversion", pct, "mejor conversión", "peor"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Quién convierte mejor a contratación?", "¿Hay psicólogos que califican muy distinto?"],
        "contexto_ia": {"kpis": k, "volumen": volumen, "puntajes": puntajes, "conversion": conversion,
                        "variabilidad": variabilidad},
    }


@catalogo.detalle("psicologos")
def detalle_psicologos(clave, valor, serie, periodo, filtros):
    condicion, params = f"{PSICOLOGO} = %s", [valor]
    if clave == "psicologo_tipo" and serie in ("Individuales", "Grupales"):
        condicion += " AND e.EntrevistaEsGrupal = %s"
        params.append("S" if serie == "Grupales" else "N")
    filas, columnas = s.entrevistas(filtros, condicion, params)
    return respuesta_detalle(f"Entrevistas de {valor}" + (f" · {serie}" if clave == "psicologo_tipo" else ""), columnas, filas)


# ==========================================================================
# 3. Calidad y puntajes (ent_cal)
# ==========================================================================
_CORTES_1_5 = [("Muy bajo (1)", "{x} < 2"), ("Bajo (2)", "{x} = 2"), ("Medio (3)", "{x} = 3"), ("Alto (4)", "{x} = 4"),
               ("Excelente (5)", "{x} >= 5")]
_CORTES_TOTAL = [("Muy bajo (2-3)", "{x} <= 3"), ("Bajo (4-5)", "{x} BETWEEN 4 AND 5"), ("Medio (6-7)", "{x} BETWEEN 6 AND 7"),
                 ("Alto (8-9)", "{x} BETWEEN 8 AND 9"), ("Excelente (10)", "{x} >= 10")]


def _condicion_corte(cortes, expresion, valor):
    return next((c.format(x=expresion) for e, c in cortes if e == valor), "1=0")


@catalogo.registrar(
    "calidad", "Calidad y puntajes",
    "Cómo se distribuyen los puntajes de formación y experiencia y si un mejor puntaje termina en contratación.",
    usa_periodo=False, icono="bi-award", filtros=[s.F_PSICOLOGO, s.F_SITUACION, s.F_DESDE, s.F_HASTA],
)
def calidad(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_entrevistas, {AVG_F} AS avg_formacion, {AVG_E} AS avg_experiencia, {AVG_T} AS avg_total,
               ROUND(ISNULL(STDEV(CASE WHEN {TOTAL} > 0 THEN {TOTAL} END), 0), 2) AS desviacion_total,
               ROUND(MAX({TOTAL}), 2) AS max_puntaje
        FROM dbo.Entrevistas e WHERE {w}""", p)

    def distribucion(expresion, cortes):
        b = _bins(expresion, cortes)
        filas = sgo.filas(f"SELECT {b} AS label, COUNT(*) AS value FROM dbo.Entrevistas e WHERE {w} GROUP BY {b} "
                          f"ORDER BY MIN({expresion})", p)
        orden = [e for e, _ in cortes]
        return sorted(filas, key=lambda r: orden.index(r["label"]) if r["label"] in orden else 99)

    formacion = distribucion(PUNTAJE_F, _CORTES_1_5)
    experiencia = distribucion(PUNTAJE_E, _CORTES_1_5)
    total_dist = distribucion(TOTAL, _CORTES_TOTAL)
    matriz = sgo.filas(f"""
        SELECT CAST(ROUND({PUNTAJE_F}, 0) AS INT) AS formacion, CAST(ROUND({PUNTAJE_E}, 0) AS INT) AS experiencia, COUNT(*) AS cantidad
        FROM dbo.Entrevistas e WHERE {w}
        GROUP BY CAST(ROUND({PUNTAJE_F}, 0) AS INT), CAST(ROUND({PUNTAJE_E}, 0) AS INT) ORDER BY formacion, experiencia""", p)
    situacion = sgo.filas(f"""
        SELECT ISNULL(sl.SituacionLaboralNombre, 'Sin especificar') AS label, {AVG_F} AS avg_formacion, {AVG_E} AS avg_experiencia,
               COUNT(*) AS total_entrevistas
        FROM dbo.Entrevistas e LEFT JOIN dbo.SituacionesLaborales sl ON e.SituacionLaboralId = sl.SituacionLaboralId
        WHERE {w} GROUP BY sl.SituacionLaboralId, sl.SituacionLaboralNombre ORDER BY total_entrevistas DESC""", p)
    b_total = _bins(TOTAL, _CORTES_TOTAL)
    correlacion = sgo.filas(f"""
        SELECT {b_total} AS label, COUNT(DISTINCT e.CandidatoId) AS total_candidatos, {CONTRATADOS} AS candidatos_contratados,
               {PCT_CONTRATO} AS pct_contratacion
        FROM dbo.Entrevistas e {JOIN_CONTRATO} WHERE {w} GROUP BY {b_total} ORDER BY MIN({TOTAL})""", p)
    tendencia = sgo.filas(f"""
        SELECT YEAR(e.EntrevistaFecha) AS anio, MONTH(e.EntrevistaFecha) AS mes,
               CAST(YEAR(e.EntrevistaFecha) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(e.EntrevistaFecha) AS VARCHAR), 2) AS label,
               {AVG_F} AS avg_formacion, {AVG_E} AS avg_experiencia, {AVG_T} AS avg_total
        FROM dbo.Entrevistas e WHERE {w} GROUP BY YEAR(e.EntrevistaFecha), MONTH(e.EntrevistaFecha) ORDER BY anio, mes""", p)

    escala = [1, 2, 3, 4, 5]
    celdas = [[escala.index(int(num(r["experiencia"]))), escala.index(int(num(r["formacion"]))), num(r["cantidad"])]
              for r in matriz if int(num(r["experiencia"])) in escala and int(num(r["formacion"])) in escala]
    alta = next((r for r in correlacion if str(r["label"]).startswith("Excelente")), None)
    baja = next((r for r in correlacion if str(r["label"]).startswith("Muy bajo")), None)
    secciones = [
        seccion(
            "Tendencia mensual de calidad",
            [f"Puntaje total promedio del último mes: {decimal(tendencia[-1]['avg_total'])}." if tendencia else "", _ESCALA],
            g.lineas([_mes(r) for r in tendencia], {"Formación": valores(tendencia, "avg_formacion"),
                                                    "Experiencia": valores(tendencia, "avg_experiencia")}),
            explicacion="Puntaje promedio de formación y de experiencia por mes (sin contar los ceros).",
        ),
        seccion(
            "Distribución del puntaje de formación",
            [lider(formacion, "label", "value", "entrevistas")],
            g.columnas(etiquetas(formacion), {"Entrevistas": valores(formacion, "value")}, rotar=0),
            explicacion="Entrevistas según el puntaje de formación (1 a 5).",
            detalle="formacion", ayuda_detalle="Hacé clic en una barra para ver esas entrevistas.",
        ),
        seccion(
            "Distribución del puntaje de experiencia",
            [lider(experiencia, "label", "value", "entrevistas")],
            g.columnas(etiquetas(experiencia), {"Entrevistas": valores(experiencia, "value")}, rotar=0,
                       colores=[g.SERIES[1]]),
            explicacion="Entrevistas según el puntaje de experiencia (1 a 5).",
            detalle="experiencia", ayuda_detalle="Hacé clic en una barra para ver esas entrevistas.",
        ),
        seccion(
            "Distribución del puntaje total",
            [lider(total_dist, "label", "value", "entrevistas")],
            g.columnas(etiquetas(total_dist), {"Entrevistas": valores(total_dist, "value")}, rotar=0, colores=[g.SERIES[2]]),
            explicacion="Suma de formación y experiencia (2 a 10).",
            detalle="total", ayuda_detalle="Hacé clic en una barra para ver esas entrevistas.",
        ),
        seccion(
            "Matriz formación × experiencia",
            ["Las celdas más oscuras muestran las combinaciones de puntaje más frecuentes."],
            g.mapa_calor([str(x) for x in escala], [str(x) for x in escala], celdas), alto=360,
            explicacion="Columnas: puntaje de experiencia; filas: puntaje de formación. Cada celda cuenta las "
                        "entrevistas con esa combinación.",
        ),
        seccion(
            "Calidad por situación laboral",
            [],
            g.columnas(etiquetas(situacion), {"Formación": valores(situacion, "avg_formacion"),
                                              "Experiencia": valores(situacion, "avg_experiencia")}),
            explicacion="Puntaje promedio de formación y experiencia según la situación laboral del candidato.",
            detalle="situacion", ayuda_detalle="Hacé clic en una situación para ver esas entrevistas.",
        ),
        seccion(
            "Correlación puntaje → contratación",
            [f"Con puntaje excelente se contrata al {pct(alta['pct_contratacion'])}; con puntaje muy bajo, al "
             f"{pct(baja['pct_contratacion'])}." if alta and baja else ""],
            g.columnas(etiquetas(correlacion), {"% contratados": valores(correlacion, "pct_contratacion")},
                       formato="fmt:pct", rotar=0),
            explicacion="Para cada rango de puntaje total, qué parte de los candidatos entrevistados ingresó después "
                        "en una asignación.",
            detalle="total", ayuda_detalle="Hacé clic en un rango para ver esas entrevistas.",
            tabla=tabla("Contratación por puntaje", ["Rango", "Candidatos", "Contratados", "% contratación"],
                        [[r["label"], entero(r["total_candidatos"]), entero(r["candidatos_contratados"]),
                          pct(r["pct_contratacion"])] for r in correlacion]),
        ),
    ]
    return {
        "kpis": [
            kpi("Total entrevistas", entero(k.get("total_entrevistas"))),
            kpi("Promedio formación", decimal(k.get("avg_formacion")), "", _ESCALA),
            kpi("Promedio experiencia", decimal(k.get("avg_experiencia"))),
            kpi("Promedio total", decimal(k.get("avg_total")), f"desvío {decimal(k.get('desviacion_total'))}"),
            kpi("Puntaje máximo", decimal(k.get("max_puntaje"))),
        ],
        "conclusiones": [
            f"El puntaje total promedio es {decimal(k.get('avg_total'))} (formación {decimal(k.get('avg_formacion'))}, "
            f"experiencia {decimal(k.get('avg_experiencia'))}).",
            f"Con puntaje excelente se contrata al {pct(alta['pct_contratacion'])} y con muy bajo al "
            f"{pct(baja['pct_contratacion'])}." if alta and baja else "",
            lider(total_dist, "label", "value", "entrevistas"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿El puntaje predice la contratación?", "¿Cómo evolucionó la calidad de los candidatos?"],
        "contexto_ia": {"kpis": k, "formacion": formacion, "experiencia": experiencia, "total": total_dist,
                        "correlacion": correlacion, "situacion": situacion},
    }


@catalogo.detalle("calidad")
def detalle_calidad(clave, valor, serie, periodo, filtros):
    extra, cols, joins = "", (), ""
    if clave == "formacion":
        condicion, params = _condicion_corte(_CORTES_1_5, PUNTAJE_F, valor), []
    elif clave == "experiencia":
        condicion, params = _condicion_corte(_CORTES_1_5, PUNTAJE_E, valor), []
    elif clave == "total":
        condicion, params = _condicion_corte(_CORTES_TOTAL, TOTAL, valor), []
        extra = ", CASE WHEN EXISTS (SELECT 1 FROM dbo.Asignaciones a2 WHERE a2.CandidatoId = e.CandidatoId " \
                "AND a2.AsignacionFechaIngreso > e.EntrevistaFecha) THEN 'Sí' ELSE 'No' END AS contratado"
        cols = ("Contratado",)
    else:
        condicion, params = _condicion_comun("situacion", valor)
        joins = _JOINS_COMUNES
    filas, columnas = s.entrevistas(filtros, condicion, params, extra=extra, joins=joins, columnas_extra=cols)
    return respuesta_detalle(f"Entrevistas · {valor}", columnas, filas)


# ==========================================================================
# 4. Análisis de candidatos (ent_can)
# ==========================================================================
_CORTES_CANT = [("1 entrevista", "= 1"), ("2 entrevistas", "= 2"), ("3 entrevistas", "= 3"),
                ("4-5 entrevistas", "BETWEEN 4 AND 5"), ("6+ entrevistas", ">= 6")]
_CASE_CANT = "CASE " + " ".join(f"WHEN COUNT(*) {c} THEN '{e}'" for e, c in _CORTES_CANT[:-1]) + " ELSE '6+ entrevistas' END"
_CORTES_GAP = [("0-30 días", "<= 30"), ("31-90 días", "BETWEEN 31 AND 90"), ("91-180 días", "BETWEEN 91 AND 180"),
               ("181-365 días", "BETWEEN 181 AND 365"), ("365+ días", "> 365")]
_GAP = "DATEDIFF(DAY, EntrevistaAnterior, EntrevistaFecha)"
_CASE_GAP = "CASE " + " ".join(f"WHEN {_GAP} {c} THEN '{e}'" for e, c in _CORTES_GAP[:-1]) + " ELSE '365+ días' END"
_CONTRATADO_ALGUNA = """CASE WHEN EXISTS (SELECT 1 FROM dbo.Asignaciones a2 WHERE a2.CandidatoId = {c}
        AND a2.AsignacionFechaIngreso > (SELECT MIN(e2.EntrevistaFecha) FROM dbo.Entrevistas e2 WHERE e2.CandidatoId = {c}))"""


def _ordenar(filas, cortes, campo="label"):
    orden = [e for e, _ in cortes]
    return sorted(filas, key=lambda r: orden.index(r[campo]) if r[campo] in orden else 99)


@catalogo.registrar(
    "candidatos", "Análisis de candidatos",
    "Cuántas veces se entrevista a cada candidato, cada cuánto vuelve y si más entrevistas terminan en contratación.",
    usa_periodo=False, icono="bi-person-lines-fill", filtros=[s.F_SITUACION, s.F_DESDE, s.F_HASTA],
)
def candidatos(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(DISTINCT e.CandidatoId) AS total_candidatos, COUNT(*) AS total_entrevistas,
               ROUND(CAST(COUNT(*) AS FLOAT) / NULLIF(COUNT(DISTINCT e.CandidatoId), 0), 2) AS avg_entrevistas_por_candidato,
               {CONTRATADOS} AS candidatos_contratados, {PCT_CONTRATO} AS pct_contratacion
        FROM dbo.Entrevistas e {JOIN_CONTRATO} WHERE {w}""", p)
    reincidentes = _ordenar(sgo.filas(f"""
        SELECT rango AS label, COUNT(*) AS value
        FROM (SELECT {_CASE_CANT} AS rango FROM dbo.Entrevistas e WHERE {w} GROUP BY e.CandidatoId) x
        GROUP BY rango""", p), _CORTES_CANT)
    gaps = _ordenar(sgo.filas(f"""
        SELECT {_CASE_GAP} AS label, COUNT(*) AS value
        FROM (SELECT e.CandidatoId, e.EntrevistaFecha,
                     LAG(e.EntrevistaFecha) OVER (PARTITION BY e.CandidatoId ORDER BY e.EntrevistaFecha) AS EntrevistaAnterior
              FROM dbo.Entrevistas e WHERE {w}) x
        WHERE EntrevistaAnterior IS NOT NULL GROUP BY {_CASE_GAP}""", p), _CORTES_GAP)
    situacion = sgo.filas(f"""
        SELECT ISNULL(sl.SituacionLaboralNombre, 'Sin especificar') AS label, COUNT(DISTINCT e.CandidatoId) AS total_candidatos,
               COUNT(*) AS total_entrevistas, {PCT_CONTRATO} AS pct_contratacion
        FROM dbo.Entrevistas e LEFT JOIN dbo.SituacionesLaborales sl ON e.SituacionLaboralId = sl.SituacionLaboralId
        {JOIN_CONTRATO} WHERE {w} GROUP BY sl.SituacionLaboralId, sl.SituacionLaboralNombre ORDER BY total_candidatos DESC""", p)
    top = sgo.filas(f"""
        SELECT TOP 15 RTRIM(c.CandidatoNombre) + ' ' + RTRIM(c.CandidatoApellido) AS candidato_nombre, COUNT(*) AS total_entrevistas,
               CONVERT(VARCHAR(10), MIN(e.EntrevistaFecha), 103) AS primera_entrevista,
               CONVERT(VARCHAR(10), MAX(e.EntrevistaFecha), 103) AS ultima_entrevista,
               DATEDIFF(DAY, MIN(e.EntrevistaFecha), MAX(e.EntrevistaFecha)) AS dias_entre_primera_y_ultima,
               CASE WHEN MAX(CASE WHEN a.AsignacionFechaIngreso > e.EntrevistaFecha THEN 1 ELSE 0 END) = 1 THEN 'Sí' ELSE 'No' END AS fue_contratado
        FROM dbo.Entrevistas e INNER JOIN dbo.Candidatos c ON e.CandidatoId = c.CandidatoId {JOIN_CONTRATO}
        WHERE {w} GROUP BY c.CandidatoId, c.CandidatoNombre, c.CandidatoApellido HAVING COUNT(*) > 1
        ORDER BY total_entrevistas DESC""", p)
    exito = _ordenar(sgo.filas(f"""
        SELECT rango AS label, SUM(1) AS total_candidatos, SUM(contratado) AS candidatos_contratados,
               ROUND(CAST(SUM(contratado) AS FLOAT) / NULLIF(SUM(1), 0) * 100, 2) AS pct_contratacion
        FROM (SELECT {_CASE_CANT} AS rango, {_CONTRATADO_ALGUNA.format(c='e.CandidatoId')} THEN 1 ELSE 0 END AS contratado
              FROM dbo.Entrevistas e WHERE {w} GROUP BY e.CandidatoId) x
        GROUP BY rango""", p), _CORTES_CANT)
    tendencia = sgo.filas(f"""
        SELECT YEAR(e.EntrevistaFecha) AS anio, MONTH(e.EntrevistaFecha) AS mes,
               CAST(YEAR(e.EntrevistaFecha) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(e.EntrevistaFecha) AS VARCHAR), 2) AS label,
               COUNT(DISTINCT e.CandidatoId) AS candidatos_unicos, COUNT(*) AS total_entrevistas
        FROM dbo.Entrevistas e WHERE {w} GROUP BY YEAR(e.EntrevistaFecha), MONTH(e.EntrevistaFecha) ORDER BY anio, mes""", p)

    repiten = total([r for r in reincidentes if r["label"] != "1 entrevista"], "value")
    secciones = [
        seccion(
            "Tendencia mensual: candidatos y entrevistas",
            ["Cuando las entrevistas superan mucho a los candidatos, hay candidatos que se entrevistan varias veces en el mes."],
            g.lineas([_mes(r) for r in tendencia], {"Entrevistas": valores(tendencia, "total_entrevistas"),
                                                    "Candidatos únicos": valores(tendencia, "candidatos_unicos")}),
            explicacion="Entrevistas por mes y candidatos distintos entrevistados.",
        ),
        seccion(
            "Candidatos reincidentes",
            [f"{entero(repiten)} candidatos tuvieron más de una entrevista "
             f"({pct(proporcion(repiten, total(reincidentes, 'value')))})."],
            g.columnas(etiquetas(reincidentes), {"Candidatos": valores(reincidentes, "value")}, rotar=0),
            explicacion="Candidatos según cuántas entrevistas tuvieron en el período.",
            detalle="reincidencia", ayuda_detalle="Hacé clic en una barra para ver esos candidatos.",
        ),
        seccion(
            "Tiempo entre entrevistas",
            [lider(gaps, "label", "value", "reentrevistas")],
            g.columnas(etiquetas(gaps), {"Entrevistas": valores(gaps, "value")}, rotar=0, colores=[g.SERIES[1]]),
            explicacion="Días entre una entrevista y la anterior del mismo candidato.",
            detalle="gap", ayuda_detalle="Hacé clic en un rango para ver esas entrevistas.",
        ),
        seccion(
            "Candidatos por situación laboral",
            [extremos(situacion, "label", "pct_contratacion", pct, "mejor contratación", "peor")],
            g.ranking(etiquetas(situacion), valores(situacion, "total_candidatos"), "Candidatos", g.SERIES[2]),
            alto=g.alto_ranking(len(situacion), 200),
            explicacion="Candidatos entrevistados según su situación laboral; en la tabla, el % que se contrató.",
            detalle="situacion", ayuda_detalle="Hacé clic en una situación para ver esos candidatos.",
            tabla=tabla("Por situación laboral", ["Situación", "Candidatos", "Entrevistas", "% contratación"],
                        [[r["label"], entero(r["total_candidatos"]), entero(r["total_entrevistas"]), pct(r["pct_contratacion"])]
                         for r in situacion]),
        ),
        seccion(
            "Tasa de éxito por cantidad de entrevistas",
            [extremos(exito, "label", "pct_contratacion", pct, "mayor éxito", "menor")],
            g.columnas(etiquetas(exito), {"% contratados": valores(exito, "pct_contratacion")}, formato="fmt:pct", rotar=0,
                       colores=[g.SERIES[2]]),
            explicacion="Para los candidatos con 1, 2, 3, 4-5 o 6+ entrevistas: qué parte ingresó en una asignación "
                        "después de su primera entrevista.",
            detalle="exito", ayuda_detalle="Hacé clic en una barra para ver esos candidatos.",
        ),
        seccion(
            "Candidatos más entrevistados",
            [],
            tabla=tabla("Top 15", ["Candidato", "Entrevistas", "Primera", "Última", "Días entre la primera y la última",
                                   "¿Contratado?"],
                        [[r["candidato_nombre"], entero(r["total_entrevistas"]), r["primera_entrevista"], r["ultima_entrevista"],
                          entero(r["dias_entre_primera_y_ultima"]), r["fue_contratado"]] for r in top]),
            explicacion="Los 15 candidatos con más entrevistas en el período.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total candidatos", entero(k.get("total_candidatos"))),
            kpi("Entrevistas por candidato", decimal(k.get("avg_entrevistas_por_candidato")), "promedio"),
            kpi("Candidatos contratados", entero(k.get("candidatos_contratados")), "ingresaron después de la entrevista"),
            kpi("Tasa de contratación", pct(k.get("pct_contratacion")), "",
                "Candidatos con una asignación posterior a la entrevista ÷ candidatos entrevistados."),
        ],
        "conclusiones": [
            f"Se entrevistó a {entero(k.get('total_candidatos'))} candidatos y se contrató al {pct(k.get('pct_contratacion'))}.",
            f"{entero(repiten)} candidatos tuvieron más de una entrevista.",
            extremos(exito, "label", "pct_contratacion", pct, "mayor tasa de éxito", "menor"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Volver a entrevistar sirve para contratar?", "¿Cada cuánto vuelven los candidatos?"],
        "contexto_ia": {"kpis": k, "reincidentes": reincidentes, "gaps": gaps, "situacion": situacion, "exito": exito},
    }


@catalogo.detalle("candidatos")
def detalle_candidatos(clave, valor, serie, periodo, filtros):
    w, p = where(filtros)
    if clave == "gap":
        condicion = next((f"DATEDIFF(DAY, eo.EntrevistaAnterior, eo.EntrevistaActual) {c}" for e, c in _CORTES_GAP if e == valor), "1=0")
        filas = sgo.filas(f"""
            SELECT TOP 500 eo.EntrevistaId, RTRIM(c.CandidatoNombre) + ' ' + RTRIM(c.CandidatoApellido) AS candidato,
                   CONVERT(VARCHAR(10), eo.EntrevistaAnterior, 103) AS anterior, CONVERT(VARCHAR(10), eo.EntrevistaActual, 103) AS actual,
                   DATEDIFF(DAY, eo.EntrevistaAnterior, eo.EntrevistaActual) AS dias,
                   ISNULL(sl.SituacionLaboralNombre, 'Sin especificar') AS situacion
            FROM (SELECT e.EntrevistaId, e.CandidatoId, e.EntrevistaFecha AS EntrevistaActual, e.SituacionLaboralId,
                         LAG(e.EntrevistaFecha) OVER (PARTITION BY e.CandidatoId ORDER BY e.EntrevistaFecha) AS EntrevistaAnterior
                  FROM dbo.Entrevistas e WHERE {w}) eo
            INNER JOIN dbo.Candidatos c ON eo.CandidatoId = c.CandidatoId
            LEFT JOIN dbo.SituacionesLaborales sl ON eo.SituacionLaboralId = sl.SituacionLaboralId
            WHERE eo.EntrevistaAnterior IS NOT NULL AND {condicion}
            ORDER BY dias, eo.EntrevistaActual DESC""", p)
        return respuesta_detalle(f"Reentrevistas · {valor}",
                                 ["Entrevista", "Candidato", "Anterior", "Actual", "Días entre", "Situación"], filas)
    having, extra_where, params = "", "", list(p)
    if clave in ("reincidencia", "exito"):
        having = "HAVING COUNT(DISTINCT e.EntrevistaId) " + next((c for e, c in _CORTES_CANT if e == valor), "= -1")
    else:  # situacion
        extra_where = "AND ISNULL(sl.SituacionLaboralNombre, 'Sin especificar') = %s"
        params.append(valor)
    filas = sgo.filas(f"""
        SELECT TOP 500 c.CandidatoId, RTRIM(MAX(c.CandidatoNombre)) + ' ' + RTRIM(MAX(c.CandidatoApellido)) AS candidato,
               COUNT(DISTINCT e.EntrevistaId) AS total_entrevistas,
               CONVERT(VARCHAR(10), MIN(e.EntrevistaFecha), 103) AS primera, CONVERT(VARCHAR(10), MAX(e.EntrevistaFecha), 103) AS ultima,
               {_CONTRATADO_ALGUNA.format(c='c.CandidatoId')} THEN 'Sí' ELSE 'No' END AS contratado,
               MAX(ISNULL(sl.SituacionLaboralNombre, 'Sin especificar')) AS situacion
        FROM dbo.Entrevistas e INNER JOIN dbo.Candidatos c ON e.CandidatoId = c.CandidatoId
        LEFT JOIN dbo.SituacionesLaborales sl ON e.SituacionLaboralId = sl.SituacionLaboralId
        WHERE {w} {extra_where} GROUP BY c.CandidatoId {having}
        ORDER BY contratado DESC, total_entrevistas DESC""", params)
    return respuesta_detalle(f"Candidatos · {valor}",
                             ["Candidato Id", "Candidato", "Entrevistas", "Primera", "Última", "Contratado", "Situación"], filas)


# ==========================================================================
# 5. Canales de publicación (ent_pub)
# ==========================================================================
@catalogo.registrar(
    "canales", "Canales de publicación",
    "Qué canales traen más entrevistas, cuáles convierten en contratación y cuáles traen mejores candidatos.",
    usa_periodo=False, icono="bi-megaphone", filtros=[s.F_CANAL, s.F_DESDE, s.F_HASTA],
)
def canales(periodo, filtros):
    w, p = where(filtros)
    join_cp = "LEFT JOIN dbo.CanalesPublicacionAvisos cp ON e.EntrevistaCanalPublicacion = cp.CanalPublicacionId"
    canal = "ISNULL(cp.CanalPublicacionDescripcion, 'Sin canal')"
    agrupa = "GROUP BY cp.CanalPublicacionId, cp.CanalPublicacionDescripcion"
    k = sgo.fila(f"""
        SELECT COUNT(DISTINCT e.EntrevistaCanalPublicacion) AS total_canales, COUNT(*) AS total_entrevistas,
               COUNT(DISTINCT e.CandidatoId) AS total_candidatos, {ASIGNADOS} AS candidatos_contratados, {PCT_ASIGNADO} AS pct_contratacion
        FROM dbo.Entrevistas e {JOIN_ASIGNADO} WHERE {w}""", p)
    volumen = sgo.filas(f"""
        SELECT {canal} AS label, COUNT(*) AS total_entrevistas, COUNT(DISTINCT e.CandidatoId) AS candidatos_unicos,
               ROUND(CAST(COUNT(*) AS FLOAT) / NULLIF(COUNT(DISTINCT e.CandidatoId), 0), 2) AS entrevistas_por_candidato
        FROM dbo.Entrevistas e {join_cp} WHERE {w} {agrupa} ORDER BY total_entrevistas DESC""", p)
    efectividad = sgo.filas(f"""
        SELECT {canal} AS label, COUNT(DISTINCT e.CandidatoId) AS total_candidatos, {ASIGNADOS} AS candidatos_contratados,
               {PCT_ASIGNADO} AS pct_contratacion
        FROM dbo.Entrevistas e {join_cp} {JOIN_ASIGNADO} WHERE {w} {agrupa}
        HAVING COUNT(DISTINCT e.CandidatoId) >= 5 ORDER BY pct_contratacion DESC""", p)
    calidad_c = sgo.filas(f"""
        SELECT {canal} AS label, {AVG_F} AS avg_formacion, {AVG_E} AS avg_experiencia, {AVG_T} AS avg_total, COUNT(*) AS total_entrevistas
        FROM dbo.Entrevistas e {join_cp} WHERE {w} {agrupa} HAVING COUNT(*) >= 10 ORDER BY avg_total DESC""", p)
    tendencia = sgo.filas(f"""
        SELECT YEAR(e.EntrevistaFecha) AS anio, MONTH(e.EntrevistaFecha) AS mes,
               CAST(YEAR(e.EntrevistaFecha) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(e.EntrevistaFecha) AS VARCHAR), 2) AS label,
               COUNT(*) AS total_entrevistas, COUNT(DISTINCT e.EntrevistaCanalPublicacion) AS canales_activos
        FROM dbo.Entrevistas e WHERE {w} GROUP BY YEAR(e.EntrevistaFecha), MONTH(e.EntrevistaFecha) ORDER BY anio, mes""", p)
    indice = sgo.filas(f"""
        SELECT {canal} AS label, COUNT(DISTINCT e.CandidatoId) AS candidatos_unicos, COUNT(*) AS total_entrevistas,
               {ASIGNADOS} AS candidatos_contratados, {PCT_ASIGNADO} AS pct_contratacion, {AVG_T} AS avg_puntaje,
               ROUND((CAST({ASIGNADOS} AS FLOAT) / NULLIF(COUNT(DISTINCT e.CandidatoId), 0) * 0.6)
                     + ((AVG(CASE WHEN {TOTAL} > 0 THEN {TOTAL} END) / 20) * 0.4) * 100, 2) AS indice_efectividad
        FROM dbo.Entrevistas e {join_cp} {JOIN_ASIGNADO} WHERE {w} {agrupa}
        HAVING COUNT(DISTINCT e.CandidatoId) >= 10 ORDER BY indice_efectividad DESC""", p)

    secciones = [
        seccion(
            "Tendencia mensual",
            [],
            g.lineas([_mes(r) for r in tendencia], {"Entrevistas": valores(tendencia, "total_entrevistas")}, area=True),
            explicacion="Entrevistas por mes. En la tabla, cuántos canales distintos se usaron cada mes.",
            tabla=tabla("Canales activos por mes", ["Mes", "Entrevistas", "Canales activos"],
                        [[_mes(r), entero(r["total_entrevistas"]), entero(r["canales_activos"])] for r in tendencia[-12:]]),
        ),
        seccion(
            "Ranking por volumen de entrevistas",
            [lider(volumen, "label", "total_entrevistas", "entrevistas"), concentracion(volumen, "total_entrevistas", 3, "entrevistas")],
            g.ranking(etiquetas(volumen), valores(volumen, "total_entrevistas"), "Entrevistas"), alto=g.alto_ranking(len(volumen)),
            explicacion="Entrevistas por canal de publicación (el market share es la parte de cada barra sobre el total).",
            detalle="canal", ayuda_detalle="Hacé clic en un canal para ver sus entrevistas.",
        ),
        seccion(
            "Efectividad por canal (% contratación)",
            [extremos(efectividad, "label", "pct_contratacion", pct, "más efectivo", "menos efectivo")],
            g.ranking(etiquetas(efectividad), valores(efectividad, "pct_contratacion"), "% contratados", g.SERIES[2],
                      formato="fmt:pct"),
            alto=g.alto_ranking(len(efectividad)),
            explicacion="Candidatos del canal que tuvieron alguna asignación ÷ candidatos del canal. Canales con 5 "
                        "candidatos o más.",
            detalle="canal", ayuda_detalle="Hacé clic en un canal para ver sus entrevistas.",
        ),
        seccion(
            "Calidad promedio por canal",
            [extremos(calidad_c, "label", "avg_total", decimal, "mejor puntaje", "peor"), _ESCALA],
            g.columnas(etiquetas(calidad_c), {"Formación": valores(calidad_c, "avg_formacion"),
                                              "Experiencia": valores(calidad_c, "avg_experiencia")}),
            explicacion="Puntaje promedio de formación y experiencia de los candidatos de cada canal (10+ entrevistas).",
            detalle="canal", ayuda_detalle="Hacé clic en un canal para ver sus entrevistas.",
        ),
        seccion(
            "Índice de efectividad de canales",
            [f"{indice[0]['label']} tiene el mejor índice ({decimal(indice[0]['indice_efectividad'])})." if indice else ""],
            tabla=tabla("Índice de efectividad", ["Canal", "Candidatos", "Entrevistas", "Contratados", "% contratación",
                                                  "Puntaje promedio", "Índice"],
                        [[r["label"], entero(r["candidatos_unicos"]), entero(r["total_entrevistas"]),
                          entero(r["candidatos_contratados"]), pct(r["pct_contratacion"]), decimal(r["avg_puntaje"]),
                          decimal(r["indice_efectividad"])] for r in indice]),
            explicacion="Índice del SGO: 60% la tasa de contratación y 40% el puntaje promedio normalizado. Canales con "
                        "10 candidatos o más.",
        ),
    ]
    return {
        "kpis": [
            kpi("Canales activos", entero(k.get("total_canales"))),
            kpi("Total entrevistas", entero(k.get("total_entrevistas"))),
            kpi("Candidatos únicos", entero(k.get("total_candidatos"))),
            kpi("Candidatos contratados", entero(k.get("candidatos_contratados")), "con alguna asignación"),
            kpi("Tasa de contratación", pct(k.get("pct_contratacion")), "global"),
        ],
        "conclusiones": [
            lider(volumen, "label", "total_entrevistas", "entrevistas"),
            extremos(efectividad, "label", "pct_contratacion", pct, "canal más efectivo", "menos efectivo"),
            f"{indice[0]['label']} tiene el mejor índice de efectividad." if indice else "",
        ],
        "secciones": secciones,
        "sugerencias": ["¿En qué canal conviene invertir?", "¿Qué canal trae mejores candidatos?"],
        "contexto_ia": {"kpis": k, "volumen": volumen, "efectividad": efectividad, "calidad": calidad_c, "indice": indice},
    }


@catalogo.detalle("canales")
def detalle_canales(clave, valor, serie, periodo, filtros):
    condicion, params = _condicion_comun("canal", valor)
    filas, columnas = s.entrevistas(filtros, condicion, params, joins=_JOINS_COMUNES)
    return respuesta_detalle(f"Entrevistas · {valor}", columnas, filas)


# ==========================================================================
# 6. Vinculación con pedidos (ent_ped)
# ==========================================================================
_CORTES_POR_PEDIDO = [("1 entrevista", "= 1"), ("2-3 entrevistas", "BETWEEN 2 AND 3"), ("4-5 entrevistas", "BETWEEN 4 AND 5"),
                      ("6-10 entrevistas", "BETWEEN 6 AND 10"), ("11+ entrevistas", "> 10")]
_DIAS_PED = "DATEDIFF(DAY, ped.PedidoFecha, e.EntrevistaFecha)"
_CORTES_TIEMPO = [("Entrevista antes del pedido", f"{_DIAS_PED} < 0"), ("0-7 días", f"{_DIAS_PED} BETWEEN 0 AND 7"),
                  ("8-14 días", f"{_DIAS_PED} BETWEEN 8 AND 14"), ("15-30 días", f"{_DIAS_PED} BETWEEN 15 AND 30"),
                  ("31-60 días", f"{_DIAS_PED} BETWEEN 31 AND 60"), ("60+ días", f"{_DIAS_PED} > 60")]


@catalogo.registrar(
    "pedidos", "Vinculación con pedidos",
    "Qué parte de las entrevistas está ligada a un pedido, cuántas hace falta por pedido y cuánto se tarda en entrevistar.",
    usa_periodo=False, icono="bi-link-45deg", filtros=[s.F_PSICOLOGO, s.F_PEDIDO, s.F_DESDE, s.F_HASTA],
)
def pedidos(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_entrevistas, COUNT(DISTINCT e.CandidatoId) AS total_candidatos,
               SUM(CASE WHEN e.EntrevistaPedidoId IS NOT NULL THEN 1 ELSE 0 END) AS entrevistas_con_pedido,
               SUM(CASE WHEN e.EntrevistaPedidoId IS NULL THEN 1 ELSE 0 END) AS entrevistas_sin_pedido,
               ROUND(CAST(SUM(CASE WHEN e.EntrevistaPedidoId IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS pct_con_pedido,
               COUNT(DISTINCT e.EntrevistaPedidoId) AS pedidos_distintos
        FROM dbo.Entrevistas e WHERE {w}""", p)
    tendencia = sgo.filas(f"""
        SELECT YEAR(e.EntrevistaFecha) AS anio, MONTH(e.EntrevistaFecha) AS mes,
               CAST(YEAR(e.EntrevistaFecha) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(e.EntrevistaFecha) AS VARCHAR), 2) AS label,
               SUM(CASE WHEN e.EntrevistaPedidoId IS NOT NULL THEN 1 ELSE 0 END) AS con_pedido,
               SUM(CASE WHEN e.EntrevistaPedidoId IS NULL THEN 1 ELSE 0 END) AS sin_pedido,
               ROUND(CAST(SUM(CASE WHEN e.EntrevistaPedidoId IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS pct_vinculacion
        FROM dbo.Entrevistas e WHERE {w} GROUP BY YEAR(e.EntrevistaFecha), MONTH(e.EntrevistaFecha) ORDER BY anio, mes""", p)
    top = sgo.filas(f"""
        SELECT TOP 15 ped.PedidoNumero, ISNULL(cli.ClienteRazonSocial, 'Cliente desconocido') AS cliente, COUNT(*) AS total_entrevistas,
               COUNT(DISTINCT e.CandidatoId) AS candidatos_unicos, {ASIGNADOS} AS candidatos_contratados, {PCT_ASIGNADO} AS pct_conversion
        FROM dbo.Entrevistas e INNER JOIN dbo.Pedidos ped ON e.EntrevistaPedidoId = ped.PedidoId
        LEFT JOIN dbo.Clientes cli ON ped.ClienteId = cli.ClienteId {JOIN_ASIGNADO}
        WHERE {w} AND e.EntrevistaPedidoId IS NOT NULL
        GROUP BY e.EntrevistaPedidoId, ped.PedidoNumero, cli.ClienteRazonSocial ORDER BY total_entrevistas DESC""", p)
    case_pp = "CASE " + " ".join(f"WHEN num_entrevistas {c} THEN '{e}'" for e, c in _CORTES_POR_PEDIDO[:-1]) + " ELSE '11+ entrevistas' END"
    por_pedido = _ordenar(sgo.filas(f"""
        WITH EntrevistasPorPedido AS (SELECT e.EntrevistaPedidoId, COUNT(*) AS num_entrevistas FROM dbo.Entrevistas e
                                      WHERE {w} AND e.EntrevistaPedidoId IS NOT NULL GROUP BY e.EntrevistaPedidoId)
        SELECT {case_pp} AS label, COUNT(*) AS cantidad_pedidos FROM EntrevistasPorPedido GROUP BY {case_pp}""", p),
        _CORTES_POR_PEDIDO)
    efectividad = sgo.filas(f"""
        SELECT CASE WHEN e.EntrevistaPedidoId IS NOT NULL THEN 'Con pedido' ELSE 'Sin pedido' END AS label,
               COUNT(DISTINCT e.CandidatoId) AS total_candidatos, {ASIGNADOS} AS candidatos_contratados,
               {PCT_ASIGNADO} AS pct_contratacion, {AVG_T} AS avg_puntaje
        FROM dbo.Entrevistas e {JOIN_ASIGNADO} WHERE {w}
        GROUP BY CASE WHEN e.EntrevistaPedidoId IS NOT NULL THEN 'Con pedido' ELSE 'Sin pedido' END""", p)
    por_psicologo = sgo.filas(f"""
        SELECT {PSICOLOGO} AS label, COUNT(*) AS total_entrevistas,
               SUM(CASE WHEN e.EntrevistaPedidoId IS NOT NULL THEN 1 ELSE 0 END) AS con_pedido,
               SUM(CASE WHEN e.EntrevistaPedidoId IS NULL THEN 1 ELSE 0 END) AS sin_pedido,
               ROUND(CAST(SUM(CASE WHEN e.EntrevistaPedidoId IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS pct_vinculacion
        FROM dbo.Entrevistas e {JOIN_PSI} WHERE {w}
        GROUP BY p.PsicologoId, p.PsicologoNombre, p.PsicologoApellido HAVING COUNT(*) >= 10 ORDER BY pct_vinculacion DESC""", p)
    case_t = "CASE " + " ".join(f"WHEN {c} THEN '{e}'" for e, c in _CORTES_TIEMPO[:-1]) + " ELSE '60+ días' END"
    tiempo = _ordenar(sgo.filas(f"""
        SELECT {case_t} AS label, COUNT(*) AS cantidad_entrevistas
        FROM dbo.Entrevistas e INNER JOIN dbo.Pedidos ped ON e.EntrevistaPedidoId = ped.PedidoId
        WHERE {w} AND e.EntrevistaPedidoId IS NOT NULL GROUP BY {case_t}""", p), _CORTES_TIEMPO)

    con = next((r for r in efectividad if r["label"] == "Con pedido"), None)
    sin = next((r for r in efectividad if r["label"] == "Sin pedido"), None)
    secciones = [
        seccion(
            "Tendencia mensual de vinculación",
            [f"En el último mes el {pct(tendencia[-1]['pct_vinculacion'])} de las entrevistas tuvo pedido." if tendencia else ""],
            g.columnas([_mes(r) for r in tendencia], {"Con pedido": valores(tendencia, "con_pedido"),
                                                      "Sin pedido": valores(tendencia, "sin_pedido")}, apiladas=True,
                       colores=[g.SERIES[0], g.NEUTRO]),
            explicacion="Entrevistas por mes, separadas entre las que tienen pedido asociado y las que no.",
        ),
        seccion(
            "Distribución de entrevistas por pedido",
            [lider(por_pedido, "label", "cantidad_pedidos", "pedidos")],
            g.columnas(etiquetas(por_pedido), {"Pedidos": valores(por_pedido, "cantidad_pedidos")}, rotar=0),
            explicacion="Pedidos según cuántas entrevistas se hicieron para cubrirlos.",
        ),
        seccion(
            "Tiempo desde el pedido hasta la entrevista",
            [lider(tiempo, "label", "cantidad_entrevistas", "entrevistas")],
            g.columnas(etiquetas(tiempo), {"Entrevistas": valores(tiempo, "cantidad_entrevistas")}, colores=[g.SERIES[1]]),
            explicacion="Días entre la fecha del pedido y la de la entrevista. «Antes del pedido» son entrevistas "
                        "registradas con fecha anterior al pedido al que se asociaron.",
            detalle="tiempo", ayuda_detalle="Hacé clic en un rango para ver esas entrevistas.",
        ),
        seccion(
            "Efectividad: con pedido vs. sin pedido",
            [f"Con pedido se contrata al {pct(con['pct_contratacion'])} y sin pedido al {pct(sin['pct_contratacion'])}."
             if con and sin else ""],
            g.columnas(etiquetas(efectividad), {"% contratados": valores(efectividad, "pct_contratacion")},
                       formato="fmt:pct", rotar=0, colores=[g.SERIES[2]]),
            explicacion="Candidatos que tuvieron alguna asignación, según si la entrevista estaba ligada a un pedido.",
            detalle="vinculo", ayuda_detalle="Hacé clic en una barra para ver esas entrevistas.",
        ),
        seccion(
            "Vinculación por psicólogo",
            [extremos(por_psicologo, "label", "pct_vinculacion", pct, "mayor vinculación", "menor")],
            g.ranking(etiquetas(por_psicologo), valores(por_psicologo, "pct_vinculacion"), "% con pedido", formato="fmt:pct"),
            alto=g.alto_ranking(len(por_psicologo)),
            explicacion="Parte de las entrevistas de cada psicólogo (10+ entrevistas) que está asociada a un pedido.",
            detalle="psicologo", ayuda_detalle="Hacé clic en un psicólogo para ver sus entrevistas.",
        ),
        seccion(
            "Top pedidos con más entrevistas",
            [],
            tabla=tabla("Top 15 pedidos", ["Pedido", "Cliente", "Entrevistas", "Candidatos", "Contratados", "% conversión"],
                        [[r["PedidoNumero"], r["cliente"], entero(r["total_entrevistas"]), entero(r["candidatos_unicos"]),
                          entero(r["candidatos_contratados"]), pct(r["pct_conversion"])] for r in top]),
            explicacion="Pedidos para los que se hicieron más entrevistas.",
        ),
    ]
    return {
        "kpis": [
            kpi("Total entrevistas", entero(k.get("total_entrevistas"))),
            kpi("Con pedido", entero(k.get("entrevistas_con_pedido"))),
            kpi("Sin pedido", entero(k.get("entrevistas_sin_pedido"))),
            kpi("% de vinculación", pct(k.get("pct_con_pedido"))),
            kpi("Pedidos distintos", entero(k.get("pedidos_distintos"))),
        ],
        "conclusiones": [
            f"{pct(k.get('pct_con_pedido'))} de las entrevistas está ligada a uno de {entero(k.get('pedidos_distintos'))} pedidos.",
            f"Con pedido se contrata al {pct(con['pct_contratacion'])} y sin pedido al {pct(sin['pct_contratacion'])}."
            if con and sin else "",
            lider(tiempo, "label", "cantidad_entrevistas", "entrevistas"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Cuántas entrevistas hacen falta por pedido?", "¿Qué tan rápido entrevistamos tras el pedido?"],
        "contexto_ia": {"kpis": k, "por_pedido": por_pedido, "tiempo": tiempo, "efectividad": efectividad,
                        "por_psicologo": por_psicologo},
    }


@catalogo.detalle("pedidos")
def detalle_pedidos(clave, valor, serie, periodo, filtros):
    joins = ""
    if clave == "tiempo":
        condicion = next((c for e, c in _CORTES_TIEMPO if e == valor), "1=0") + " AND e.EntrevistaPedidoId IS NOT NULL"
        params, joins = [], "INNER JOIN dbo.Pedidos ped ON e.EntrevistaPedidoId = ped.PedidoId"
    else:
        condicion, params = _condicion_comun(clave, valor)
    filas, columnas = s.entrevistas(filtros, condicion, params, joins=joins)
    return respuesta_detalle(f"Entrevistas · {valor}", columnas, filas)


# ==========================================================================
# 7 y 8. Análisis cualitativo y perfil psicológico (ent_cua, ent_psi)
#        Los textos de la entrevista se clasifican con palabras clave, como en el SGO.
# ==========================================================================
_SELECT_TEXTO = f"""
    SELECT e.EntrevistaId, RTRIM(c.CandidatoNombre) + ' ' + RTRIM(c.CandidatoApellido) AS candidato,
           CONVERT(VARCHAR(10), e.EntrevistaFecha, 103) AS fecha, {TOTAL} AS puntaje_total,
           CASE WHEN EXISTS (SELECT 1 FROM dbo.Asignaciones a WHERE a.CandidatoId = e.CandidatoId) THEN 'Sí' ELSE 'No' END AS contratado,
           {{campos}}
    FROM dbo.Entrevistas e INNER JOIN dbo.Candidatos c ON e.CandidatoId = c.CandidatoId
    WHERE {{w}} {{condicion}}"""

# clave -> (campos SQL, condición extra, función que clasifica la fila, campo de texto para el modal, título)
CLASIFICACIONES = {
    "sentimiento": ("e.EntrevistaResumen AS texto", "AND LEN(ISNULL(e.EntrevistaResumen, '')) > 50",
                    lambda f: [s.sentimiento(f["texto"])], "Análisis de sentimiento"),
    "perfil": ("e.EntrevistaResumen AS texto", "AND LEN(ISNULL(e.EntrevistaResumen, '')) > 50",
               lambda f: [s.perfil(f["texto"])], "Perfiles profesionales detectados"),
    "alertas": ("e.EntrevistaResumen AS texto", "AND LEN(ISNULL(e.EntrevistaResumen, '')) > 50",
                lambda f: s.alertas(f["texto"]), "Alertas detectadas"),
    "habilidades": ("e.EntrevistaResumen AS texto", "AND LEN(ISNULL(e.EntrevistaResumen, '')) > 50",
                    lambda f: [s.habilidades(f["texto"])], "Tipo de habilidades mencionadas"),
    "hobbies": ("e.EntrevistaActividadesTLibre AS texto", "AND LEN(ISNULL(e.EntrevistaActividadesTLibre, '')) > 10",
                lambda f: [s.hobby(f["texto"])], "Categorías de hobbies"),
    "familia": ("e.EntrevistaGrupoFamiliar AS texto", "AND LEN(ISNULL(e.EntrevistaGrupoFamiliar, '')) > 10",
                lambda f: [s.grupo_familiar(f["texto"])], "Composición del grupo familiar"),
    "impedimentos": ("e.EntrevistaImpedimentos AS texto", "", lambda f: [s.impedimento(f["texto"])],
                     "Impedimentos físicos"),
    "autoconocimiento": ("e.EntrevistaFortalezas AS fortalezas, e.EntrevistaDebilidades AS texto", "",
                         lambda f: [s.autoconocimiento(f["fortalezas"], f["texto"])], "Nivel de autoconocimiento"),
    "motivacion": ("e.EntrevistaMotivacion AS texto", "AND LEN(ISNULL(e.EntrevistaMotivacion, '')) > 20",
                   lambda f: [s.motivacion(f["texto"])], "Tipos de motivación"),
    "liderazgo": ("e.EntrevistaTipoSupervisor AS texto, e.EntrevistaAspectosJefe AS aspectos",
                  "AND LEN(ISNULL(e.EntrevistaTipoSupervisor, '')) > 20",
                  lambda f: [s.liderazgo(f["texto"], f["aspectos"])], "Estilo de liderazgo preferido"),
    "estres": ("e.EntrevistaSituacionEstresante AS texto", "AND LEN(ISNULL(e.EntrevistaSituacionEstresante, '')) > 30",
               lambda f: [s.manejo_estres(f["texto"])], "Manejo de situaciones estresantes"),
    "cambio": ("e.EntrevistaCambiar AS texto", "AND LEN(ISNULL(e.EntrevistaCambiar, '')) > 20",
               lambda f: [s.motivo_cambio(f["texto"])], "Motivos para cambiar de trabajo"),
}


def _clasificar(clave, filtros):
    """{categoría: [filas]} para una de las clasificaciones de texto."""
    campos, condicion, funcion, _ = CLASIFICACIONES[clave]
    w, p = where(filtros)
    grupos = defaultdict(list)
    for f in sgo.filas(_SELECT_TEXTO.format(campos=campos, w=w, condicion=condicion), p):
        for categoria in funcion(f):
            grupos[categoria].append(f)
    return grupos


def _seccion_texto(clave, filtros, explicacion, ranking=True):
    grupos = _clasificar(clave, filtros)
    filas = sorted(({"label": k, "value": len(v), "contratados": sum(1 for x in v if x.get("contratado") == "Sí")}
                    for k, v in grupos.items()), key=lambda r: -r["value"])
    titulo = CLASIFICACIONES[clave][3]
    grafico = (g.ranking(etiquetas(filas), valores(filas, "value"), "Entrevistas") if ranking
               else g.torta([(r["label"], r["value"]) for r in filas]))
    return seccion(
        titulo, [lider(filas, "label", "value", "entrevistas")], grafico,
        alto=g.alto_ranking(len(filas), 200) if ranking else 320,
        explicacion=explicacion, detalle=clave, ayuda_detalle="Hacé clic en una categoría para ver esas entrevistas.",
    ), filas


def _detalle_texto(clave, valor, filtros):
    filas = _clasificar(clave, filtros).get(valor, [])[:500]
    resultado = [[f["EntrevistaId"], f["candidato"], f["fecha"], f["puntaje_total"], f["contratado"],
                  (str(f.get("texto") or "")[:220] + ("…" if len(str(f.get("texto") or "")) > 220 else ""))]
                 for f in filas]
    return {"titulo": f"{CLASIFICACIONES[clave][3]} · {valor}",
            "columnas": ["Entrevista", "Candidato", "Fecha", "Puntaje", "Contratado", "Texto"], "filas": resultado}


@catalogo.registrar(
    "cualitativo", "Análisis cualitativo",
    "Qué dicen los resúmenes de las entrevistas: sentimiento, perfil, alertas, habilidades, hobbies, familia e impedimentos.",
    usa_periodo=False, icono="bi-chat-left-quote", filtros=[s.F_PSICOLOGO, s.F_DESDE_ANIO, s.F_HASTA],
)
def cualitativo(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_entrevistas,
               SUM(CASE WHEN LEN(ISNULL(e.EntrevistaResumen, '')) > 0 THEN 1 ELSE 0 END) AS con_resumen,
               SUM(CASE WHEN LEN(ISNULL(e.EntrevistaActividadesTLibre, '')) > 0 THEN 1 ELSE 0 END) AS con_hobbies,
               SUM(CASE WHEN LEN(ISNULL(e.EntrevistaGrupoFamiliar, '')) > 0 THEN 1 ELSE 0 END) AS con_grupo_familiar,
               SUM(CASE WHEN LEN(ISNULL(e.EntrevistaImpedimentos, '')) > 0 THEN 1 ELSE 0 END) AS con_impedimentos,
               ROUND(AVG(LEN(ISNULL(e.EntrevistaResumen, ''))), 0) AS avg_longitud_resumen
        FROM dbo.Entrevistas e WHERE {w}""", p)
    sec_sent, sent = _seccion_texto("sentimiento", filtros, "Cada resumen se clasifica según tenga más palabras positivas "
                                    "(excelente, proactivo, responsable…) o negativas (deficiente, inseguro, falta…).", False)
    sec_perfil, perfiles = _seccion_texto("perfil", filtros, "Perfil con más palabras clave en el resumen (ventas, "
                                          "administración, sistemas, producción, supervisión…).")
    sec_alertas, alertas = _seccion_texto("alertas", filtros, "Palabras de alerta en el resumen. Una entrevista puede "
                                          "tener más de una alerta.")
    sec_hab, _ = _seccion_texto("habilidades", filtros, "Si el resumen menciona más habilidades técnicas (Excel, sistemas, "
                                "contabilidad…) o blandas (comunicación, liderazgo, equipo…).", False)
    sec_hob, _ = _seccion_texto("hobbies", filtros, "Categoría de las actividades de tiempo libre declaradas.")
    sec_fam, _ = _seccion_texto("familia", filtros, "Con quién vive el candidato según el grupo familiar registrado.", False)
    sec_imp, _ = _seccion_texto("impedimentos", filtros, "Impedimentos físicos mencionados en la entrevista.")

    largos = ["Sin resumen", "Muy breve (1-49 caracteres)", "Breve (50-200 caracteres)", "Medio (201-500 caracteres)",
              "Extenso (501-1000 caracteres)", "Muy extenso (1000+ caracteres)"]
    largo = "LEN(ISNULL(e.EntrevistaResumen, ''))"
    case_l = (f"CASE WHEN {largo} = 0 THEN '{largos[0]}' WHEN {largo} < 50 THEN '{largos[1]}' "
              f"WHEN {largo} BETWEEN 50 AND 200 THEN '{largos[2]}' WHEN {largo} BETWEEN 201 AND 500 THEN '{largos[3]}' "
              f"WHEN {largo} BETWEEN 501 AND 1000 THEN '{largos[4]}' ELSE '{largos[5]}' END")
    longitud = sgo.filas(f"SELECT {case_l} AS label, COUNT(*) AS cantidad FROM dbo.Entrevistas e WHERE {w} "
                         f"GROUP BY {case_l} ORDER BY MIN({largo})", p)
    tendencia = sgo.filas(f"""
        SELECT YEAR(e.EntrevistaFecha) AS anio, MONTH(e.EntrevistaFecha) AS mes,
               CAST(YEAR(e.EntrevistaFecha) AS VARCHAR) + '-' + RIGHT('0' + CAST(MONTH(e.EntrevistaFecha) AS VARCHAR), 2) AS label,
               COUNT(*) AS total_entrevistas,
               ROUND(CAST(SUM(CASE WHEN {largo} > 0 THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS pct_con_observaciones
        FROM dbo.Entrevistas e WHERE {w} GROUP BY YEAR(e.EntrevistaFecha), MONTH(e.EntrevistaFecha) ORDER BY anio, mes""", p)
    por_psicologo = sgo.filas(f"""
        SELECT {PSICOLOGO} AS label, COUNT(*) AS total_entrevistas,
               SUM(CASE WHEN {largo} > 0 THEN 1 ELSE 0 END) AS con_observaciones,
               ROUND(CAST(SUM(CASE WHEN {largo} > 0 THEN 1 ELSE 0 END) AS FLOAT) / NULLIF(COUNT(*), 0) * 100, 2) AS pct_observaciones
        FROM dbo.Entrevistas e {JOIN_PSI} WHERE {w}
        GROUP BY p.PsicologoId, p.PsicologoNombre, p.PsicologoApellido HAVING COUNT(*) >= 5 ORDER BY pct_observaciones DESC""", p)
    case_c = (f"CASE WHEN {largo} = 0 THEN 'Sin resumen' WHEN {largo} < 100 THEN 'Resumen breve' "
              f"WHEN {largo} BETWEEN 100 AND 300 THEN 'Resumen medio' ELSE 'Resumen extenso' END")
    correlacion = sgo.filas(f"""
        SELECT {case_c} AS categoria, COUNT(*) AS total_entrevistas, {AVG_T} AS avg_puntaje,
               {ASIGNADOS} AS candidatos_contratados, {PCT_ASIGNADO} AS pct_contratacion
        FROM dbo.Entrevistas e {JOIN_ASIGNADO} WHERE {w} GROUP BY {case_c} ORDER BY MIN({largo})""", p)

    positivas = next((r["value"] for r in sent if r["label"] == "Positivo"), 0)
    sin_alertas = next((r["value"] for r in alertas if r["label"] == "Sin alertas"), 0)
    secciones = [
        sec_sent, sec_perfil, sec_alertas, sec_hab, sec_hob, sec_fam, sec_imp,
        seccion(
            "Tendencia de completitud",
            [f"En el último mes el {pct(tendencia[-1]['pct_con_observaciones'])} de las entrevistas tuvo resumen."
             if tendencia else ""],
            g.lineas([_mes(r) for r in tendencia], {"% con resumen": valores(tendencia, "pct_con_observaciones")},
                     formato="fmt:pct"),
            explicacion="Parte de las entrevistas de cada mes que tiene el resumen completo.",
        ),
        seccion(
            "Distribución por longitud del resumen",
            [lider(longitud, "label", "cantidad", "entrevistas")],
            g.columnas(etiquetas(longitud), {"Entrevistas": valores(longitud, "cantidad")}),
            explicacion="Entrevistas según la cantidad de caracteres del resumen.",
        ),
        seccion(
            "Completitud por psicólogo",
            [extremos(por_psicologo, "label", "pct_observaciones", pct, "más completo", "menos completo")],
            g.ranking(etiquetas(por_psicologo), valores(por_psicologo, "pct_observaciones"), "% con resumen",
                      formato="fmt:pct"),
            alto=g.alto_ranking(len(por_psicologo)),
            explicacion="Parte de las entrevistas de cada psicólogo (5 o más) con resumen.",
        ),
        seccion(
            "Correlación: completitud vs. calidad",
            [],
            tabla=tabla("Según el largo del resumen", ["Resumen", "Entrevistas", "Puntaje promedio", "Contratados", "% contratación"],
                        [[r["categoria"], entero(r["total_entrevistas"]), decimal(r["avg_puntaje"]),
                          entero(r["candidatos_contratados"]), pct(r["pct_contratacion"])] for r in correlacion]),
            explicacion="Si las entrevistas con resúmenes más completos tienen mejor puntaje y más contratación.",
        ),
    ]
    con_resumen = num(k.get("con_resumen"))
    return {
        "kpis": [
            kpi("Total entrevistas", entero(k.get("total_entrevistas"))),
            kpi("Con resumen", entero(con_resumen), pct(proporcion(con_resumen, k.get("total_entrevistas"))),
                f"Largo promedio: {entero(k.get('avg_longitud_resumen'))} caracteres."),
            kpi("Con hobbies", entero(k.get("con_hobbies"))),
            kpi("Con grupo familiar", entero(k.get("con_grupo_familiar"))),
            kpi("Con impedimentos", entero(k.get("con_impedimentos"))),
        ],
        "conclusiones": [
            f"{pct(proporcion(con_resumen, k.get('total_entrevistas')))} de las entrevistas tiene resumen.",
            f"{pct(proporcion(positivas, total(sent, 'value')))} de los resúmenes tiene tono positivo.",
            f"{pct(proporcion(sin_alertas, total(alertas, 'value')))} de los resúmenes no tiene alertas.",
            lider(perfiles, "label", "value", "entrevistas"),
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué alertas aparecen más?", "¿Qué psicólogos completan menos los resúmenes?"],
        "contexto_ia": {"kpis": k, "sentimiento": sent, "perfiles": perfiles, "alertas": alertas},
    }


@catalogo.detalle("cualitativo")
def detalle_cualitativo(clave, valor, serie, periodo, filtros):
    if clave not in CLASIFICACIONES:
        return {"titulo": "Sin detalle", "columnas": [], "filas": []}
    return _detalle_texto(clave, valor, filtros)


@catalogo.registrar(
    "psicologico", "Perfil psicológico",
    "Autoconocimiento, motivación, liderazgo preferido, manejo del estrés y motivos de cambio de los candidatos.",
    usa_periodo=False, icono="bi-emoji-smile", filtros=[s.F_PSICOLOGO, s.F_DESDE_ANIO, s.F_HASTA],
)
def psicologico(periodo, filtros):
    w, p = where(filtros)
    k = sgo.fila(f"""
        SELECT COUNT(*) AS total_entrevistas,
               SUM(CASE WHEN LEN(ISNULL(e.EntrevistaFortalezas, '')) > 50 AND LEN(ISNULL(e.EntrevistaDebilidades, '')) > 50 THEN 1 ELSE 0 END) AS con_autoconocimiento,
               SUM(CASE WHEN LEN(ISNULL(e.EntrevistaMotivacion, '')) > 50 THEN 1 ELSE 0 END) AS con_motivacion,
               SUM(CASE WHEN LEN(ISNULL(e.EntrevistaSituacionEstresante, '')) > 50 THEN 1 ELSE 0 END) AS con_manejo_estres,
               SUM(CASE WHEN LEN(ISNULL(e.EntrevistaTipoSupervisor, '')) > 30 THEN 1 ELSE 0 END) AS con_preferencia_lider,
               ROUND(AVG({TOTAL}), 2) AS puntaje_promedio
        FROM dbo.Entrevistas e WHERE {w}""", p)
    sec_auto, auto = _seccion_texto("autoconocimiento", filtros,
                                    "Según el largo de fortalezas y debilidades declaradas. «Defensivo»: describe "
                                    "fortalezas pero no debilidades, o usa clichés (perfeccionista, exigente…).", False)
    sec_mot, mot = _seccion_texto("motivacion", filtros, "Motivación principal según palabras clave (desarrollo, salario, "
                                  "familia, estabilidad, reconocimiento…).")
    sec_lid, lid = _seccion_texto("liderazgo", filtros, "Tipo de jefe que prefiere el candidato: coach, directivo, "
                                  "participativo o delegador.")
    sec_est, est = _seccion_texto("estres", filtros, "Cómo cuenta una situación estresante: resolviéndola, aprendiendo, "
                                  "reaccionando o minimizándola.", False)
    sec_cam, cam = _seccion_texto("cambio", filtros, "Por qué quiere cambiar de trabajo.")
    largo_f, largo_d = "LEN(ISNULL(e.EntrevistaFortalezas, ''))", "LEN(ISNULL(e.EntrevistaDebilidades, ''))"
    case_a = (f"CASE WHEN {largo_f} > 100 AND {largo_d} > 100 THEN 'Alto' "
              f"WHEN {largo_f} > 50 AND {largo_d} > 50 THEN 'Medio' ELSE 'Bajo' END")
    correlacion = sgo.filas(f"""
        SELECT {case_a} AS label, COUNT(*) AS total_entrevistas,
               COUNT(DISTINCT CASE WHEN contratados.CandidatoId IS NOT NULL THEN e.CandidatoId END) AS candidatos_contratados,
               ROUND(CAST(COUNT(DISTINCT CASE WHEN contratados.CandidatoId IS NOT NULL THEN e.CandidatoId END) AS FLOAT)
                     / NULLIF(COUNT(DISTINCT e.CandidatoId), 0) * 100, 2) AS pct_contratacion,
               ROUND(AVG({TOTAL}), 2) AS puntaje_promedio
        FROM dbo.Entrevistas e {JOIN_ASIGNADO} WHERE {w} GROUP BY {case_a}""", p)
    correlacion = sorted(correlacion, key=lambda r: ["Alto", "Medio", "Bajo"].index(r["label"])
                         if r["label"] in ("Alto", "Medio", "Bajo") else 9)
    alto = next((r for r in correlacion if r["label"] == "Alto"), None)
    bajo = next((r for r in correlacion if r["label"] == "Bajo"), None)
    secciones = [
        sec_auto, sec_mot, sec_lid, sec_est, sec_cam,
        seccion(
            "Autoconocimiento vs. tasa de contratación",
            [f"Con autoconocimiento alto se contrata al {pct(alto['pct_contratacion'])}; con bajo, al "
             f"{pct(bajo['pct_contratacion'])}." if alto and bajo else ""],
            g.columnas(etiquetas(correlacion), {"% contratados": valores(correlacion, "pct_contratacion")},
                       formato="fmt:pct", rotar=0, colores=[g.SERIES[2]]),
            explicacion="Nivel según el largo de fortalezas y debilidades, y qué parte de esos candidatos tuvo alguna asignación.",
            tabla=tabla("Autoconocimiento y resultados", ["Nivel", "Entrevistas", "Contratados", "% contratación", "Puntaje"],
                        [[r["label"], entero(r["total_entrevistas"]), entero(r["candidatos_contratados"]),
                          pct(r["pct_contratacion"]), decimal(r["puntaje_promedio"])] for r in correlacion]),
        ),
    ]
    return {
        "kpis": [
            kpi("Total entrevistas", entero(k.get("total_entrevistas"))),
            kpi("Con autoconocimiento", entero(k.get("con_autoconocimiento")), "fortalezas y debilidades completas"),
            kpi("Con motivación definida", entero(k.get("con_motivacion"))),
            kpi("Manejo de estrés", entero(k.get("con_manejo_estres")), "con situación descripta"),
            kpi("Preferencia de líder", entero(k.get("con_preferencia_lider"))),
            kpi("Puntaje promedio", decimal(k.get("puntaje_promedio")), "", _ESCALA),
        ],
        "conclusiones": [
            lider(mot, "label", "value", "candidatos"),
            lider(lid, "label", "value", "candidatos"),
            f"Con autoconocimiento alto se contrata al {pct(alto['pct_contratacion'])} y con bajo al "
            f"{pct(bajo['pct_contratacion'])}." if alto and bajo else "",
        ],
        "secciones": secciones,
        "sugerencias": ["¿Qué motiva a los candidatos?", "¿El autoconocimiento se relaciona con la contratación?"],
        "contexto_ia": {"kpis": k, "autoconocimiento": auto, "motivacion": mot, "liderazgo": lid, "estres": est,
                        "cambio": cam, "correlacion": correlacion},
    }


@catalogo.detalle("psicologico")
def detalle_psicologico(clave, valor, serie, periodo, filtros):
    if clave not in CLASIFICACIONES:
        return {"titulo": "Sin detalle", "columnas": [], "filas": []}
    return _detalle_texto(clave, valor, filtros)
