"""
Análisis del módulo Candidatos web.

Cada análisis es una pantalla del menú. Todos los gráficos tienen detalle:
al hacer clic se abre un modal con los registros (ver detalle() al final).
"""
from collections import Counter

from apps.core import graficos as g
from apps.core.analisis import Catalogo, seccion
from apps.core.estadistica import mediana, pronostico
from apps.core.utils import (
    contar_por_mes, etiqueta_mes, formato_numero, formato_pct, formato_pesos, meses_completos, siguientes_meses,
)

from . import cv, services
from .services import ETAPAS, SI

catalogo = Catalogo()

PERIODOS_WEB = {"todos": "Todos", "365": "Actualizados en el último año", "90": "En los últimos 90 días"}
CON_PERIODO = {"periodos": PERIODOS_WEB, "periodo_defecto": "todos"}
# Análisis que siempre miran toda la base (sin selector de período)
FOTO = {"usa_periodo": False, "periodos": PERIODOS_WEB, "periodo_defecto": "todos"}

TRAMOS = [(18, 24), (25, 29), (30, 34), (35, 39), (40, 44), (45, 49), (50, 64)]
TRAMOS_ETIQ = [f"{a}–{b}" if b < 64 else f"{a}+" for a, b in TRAMOS]
ANTIGUEDAD = [("Menos de 1 mes", 0, 30), ("1 a 3 meses", 31, 90), ("3 a 6 meses", 91, 180),
              ("6 meses a 1 año", 181, 365), ("1 a 2 años", 366, 730), ("Más de 2 años", 731, 99999)]
RANGOS_SALARIO = [("Hasta $ 30.000", 0, 30000), ("$ 30.001 a 40.000", 30001, 40000),
                  ("$ 40.001 a 50.000", 40001, 50000), ("$ 50.001 a 60.000", 50001, 60000),
                  ("$ 60.001 a 80.000", 60001, 80000), ("Más de $ 80.000", 80001, 10 ** 9)]
ATRIBUTOS = {"Horario completo": "disponibilidad", "Horario rotativo": "rotativo",
             "Acepta zafrales": "zafrales", "Libreta de conducir": "libreta"}
CAMPOS = {"Email": lambda f: bool(f["email"]), "Celular": lambda f: bool(f["celular"]),
          "Documento": lambda f: bool(f["documento"]), "Departamento": lambda f: bool(f["departamento"]),
          "Salario aspirado": lambda f: f["salario_aspirado"] > 0, "CV adjunto": lambda f: f["cv"]}


def _pct(a, b):
    return round(a / b * 100) if b else 0


def _tramo(edad):
    for etiq, (a, b) in zip(TRAMOS_ETIQ, TRAMOS):
        if a <= edad <= b:
            return etiq
    return TRAMOS_ETIQ[-1]


def _antiguedad(dias):
    for etiq, a, b in ANTIGUEDAD:
        if a <= dias <= b:
            return etiq
    return ANTIGUEDAD[-1][0]


def _rango(salario):
    for etiq, a, b in RANGOS_SALARIO:
        if a <= salario <= b:
            return etiq
    return RANGOS_SALARIO[-1][0]


def _requisitos(f):
    return sum(f[c] == SI for c in ATRIBUTOS.values())


def _depto(f):
    return f["departamento"] or "Sin dato"


def _barras_h(nombre, etiquetas, valores, color=None, formato="{c}", alto_barra=22):
    """Barras horizontales con etiqueta al final, para rankings."""
    return g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        grid={"left": 8, "right": 56, "top": 8, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores(),
        yAxis=g.eje_categorias(etiquetas, inverse=True),
        series=[g.barras(nombre, valores, color or g.SERIES[0], barMaxWidth=alto_barra,
                         itemStyle={"color": color or g.SERIES[0], "borderRadius": [0, 4, 4, 0]},
                         label={"show": True, "position": "right", "formatter": formato, "color": g.TINTA_SUAVE})],
    )


# ==========================================================================
# 1. Actividad en el portal
# ==========================================================================
@catalogo.registrar(
    "actividad", "Actividad en el portal",
    "Cuántos registros se actualizan por mes, qué se espera y qué parte de la base está desactualizada.",
    icono="bi-activity", **FOTO,
)
def actividad(periodo):
    todos = services.registros()
    meses = meses_completos(24)
    serie = contar_por_mes(todos, meses, campo="fecha_act")
    p = pronostico(serie, pasos=3)
    futuros = siguientes_meses(meses[-1], 3)
    grafico_meses = g.serie_pronostico(serie[-12:], p, [etiqueta_mes(*m) for m in meses[-12:]],
                                       [etiqueta_mes(*m) for m in futuros], nombre="Registros actualizados")

    antig = Counter(_antiguedad(f["dias_act"]) for f in todos)
    valores = [antig[e] for e, _, _ in ANTIGUEDAD]
    colores = [g.AZUL[5], g.AZUL[4], g.AZUL[3], g.AZUL[2], g.NARANJA[2], g.NARANJA[4]]
    grafico_antig = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        xAxis=g.eje_categorias([e for e, _, _ in ANTIGUEDAD]),
        yAxis=g.eje_valores(),
        series=[g.barras("Registros", [{"value": v, "itemStyle": {"color": c}} for v, c in zip(valores, colores)],
                         label={"show": True, "position": "top", "color": g.TINTA_SUAVE})],
    )
    viejos = sum(1 for f in todos if f["dias_act"] > 365)
    recientes = sum(1 for f in todos if f["dias_act"] <= 90)
    var = round((sum(serie[-3:]) - sum(serie[-15:-12])) / sum(serie[-15:-12]) * 100) if sum(serie[-15:-12]) else 0

    return {
        "kpis": [
            {"label": "Registros en la base", "valor": formato_numero(len(todos)), "detalle": "candidatos web"},
            {"label": "Actualizados en 90 días", "valor": formato_numero(recientes),
             "detalle": f"{_pct(recientes, len(todos))}% de la base"},
            {"label": "Sin actualizar hace más de 1 año", "valor": formato_numero(viejos), "alerta": _pct(viejos, len(todos)) > 30,
             "detalle": f"{_pct(viejos, len(todos))}% de la base"},
            {"label": f"Esperados en {etiqueta_mes(*futuros[0])}", "valor": round(p["valores"][0]),
             "detalle": f"entre {round(p['inferior'][0])} y {round(p['superior'][0])} actualizaciones"},
        ],
        "conclusiones": [
            f"La actividad de los últimos 3 meses es {abs(var)}% {'mayor' if var >= 0 else 'menor'} que en los mismos meses del año pasado.",
            f"El {_pct(viejos, len(todos))}% de la base no se actualiza hace más de un año: esos datos probablemente estén viejos.",
            f"Para {etiqueta_mes(*futuros[0])} se esperan unas {round(p['valores'][0])} actualizaciones.",
            "Una campaña para que los registrados viejos actualicen su perfil recuperaría candidatos sin costo de publicación.",
        ],
        "secciones": [
            seccion("Actualizaciones por mes", grafico=grafico_meses, detalle="mes",
                    ayuda_detalle="Hacé clic en un mes para ver quiénes actualizaron su registro.",
                    explicacion="Cada punto es la cantidad de registros cuya última actualización cayó en ese mes. "
                                "La línea punteada es la proyección y la banda celeste el rango donde debería caer "
                                "con 80% de probabilidad. Como la tabla no tiene fecha de alta, un registro nuevo y uno "
                                "viejo que se actualizó cuentan igual.",
                    lectura=[f"El último mes completo tuvo {serie[-1]} actualizaciones.",
                             "Un registro que se actualiza varias veces cuenta solo en el mes de su última actualización."]),
            seccion("Qué tan actualizada está la base", grafico=grafico_antig, detalle="antiguedad",
                    ayuda_detalle="Hacé clic en una barra para ver los registros de ese grupo.",
                    explicacion="Agrupa todos los registros según cuánto hace que se actualizaron por última vez. "
                                "En azul los vigentes (menos de un año) y en naranja los que conviene revisar.",
                    lectura=[f"{formato_numero(viejos)} registros no se tocan hace más de un año.",
                             "Un candidato con datos de hace dos años puede tener otro teléfono, otro empleo o ya no buscar trabajo."],
                    acciones=[{"prioridad": "media", "titulo": "Campaña de actualización de perfiles",
                               "detalle": f"Enviar un email a los {formato_numero(viejos)} registros con más de un año "
                                          "sin actualizar invitándolos a revisar sus datos y subir el CV."}]),
        ],
        "sugerencias": ["¿Cuántos registros activos tenemos realmente?", "¿Conviene limpiar los registros viejos?"],
        "contexto_ia": {"total": len(todos), "actualizados_90d": recientes, "sin_actualizar_1_anio": viejos,
                        "por_mes": dict(zip([etiqueta_mes(*m) for m in meses[-12:]], serie[-12:]))},
    }


# ==========================================================================
# 2. Perfil de los registrados
# ==========================================================================
@catalogo.registrar(
    "perfil", "Perfil de los registrados",
    "Edad, sexo y estado civil de las personas registradas en el portal.",
    icono="bi-person-lines-fill", **CON_PERIODO,
)
def perfil(periodo):
    filas = services.registros(periodo)
    total = len(filas)
    mujeres = [sum(1 for f in filas if f["sexo"] == "F" and _tramo(f["edad"]) == t) for t in TRAMOS_ETIQ]
    hombres = [sum(1 for f in filas if f["sexo"] == "M" and _tramo(f["edad"]) == t) for t in TRAMOS_ETIQ]
    grafico_piramide = g.base(
        legend=g.leyenda(data=["Mujeres", "Hombres"]),
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        xAxis=g.eje_valores(axisLabel={"formatter": "fmt:abs", "color": g.TINTA_SUAVE}),
        yAxis=g.eje_categorias(TRAMOS_ETIQ, name="Edad", nameLocation="end"),
        series=[
            {"name": "Mujeres", "type": "bar", "stack": "p", "barMaxWidth": 26, "data": [-v for v in mujeres],
             "itemStyle": {"color": g.SERIES[1], "borderRadius": [4, 0, 0, 4]}, "tooltip": {"valueFormatter": "fmt:abs"}},
            {"name": "Hombres", "type": "bar", "stack": "p", "barMaxWidth": 26, "data": hombres,
             "itemStyle": {"color": g.SERIES[0], "borderRadius": [0, 4, 4, 0]}},
        ],
    )
    tramo_top = max(range(len(TRAMOS)), key=lambda i: mujeres[i] + hombres[i])
    menores_30 = sum(1 for f in filas if f["edad"] < 30)

    civil = Counter(f["estado_civil"] for f in filas).most_common()
    grafico_civil = _barras_h("Registrados", [c for c, _ in civil], [v for _, v in civil], g.SERIES[2])

    return {
        "kpis": [
            {"label": "Registrados", "valor": formato_numero(total), "detalle": PERIODOS_WEB[periodo].lower()},
            {"label": "Edad mediana", "valor": round(mediana([f["edad"] for f in filas])), "detalle": "años"},
            {"label": "Mujeres", "valor": f"{_pct(sum(mujeres), total)}%", "detalle": f"{formato_numero(sum(mujeres))} registradas"},
            {"label": "Menores de 30", "valor": f"{_pct(menores_30, total)}%", "detalle": f"{formato_numero(menores_30)} personas"},
        ],
        "conclusiones": [
            f"El tramo de edad con más registrados es {TRAMOS_ETIQ[tramo_top]} años.",
            f"{_pct(menores_30, total)}% tiene menos de 30 años: la base es joven, buena para puestos de entrada.",
            f"{_pct(sum(mujeres), total)}% son mujeres.",
            f"{civil[0][0]} es el estado civil más común ({_pct(civil[0][1], total)}%).",
        ],
        "secciones": [
            seccion("Edad y sexo", grafico=grafico_piramide, alto=340, detalle="tramo",
                    ayuda_detalle="Hacé clic en una barra para ver las personas de ese tramo y sexo.",
                    explicacion="Pirámide de edades: cada fila es un tramo de edad; las barras naranjas a la izquierda "
                                "son mujeres y las azules a la derecha, hombres. Cuanto más larga la barra, más registrados.",
                    lectura=[f"El tramo {TRAMOS_ETIQ[tramo_top]} reúne {mujeres[tramo_top] + hombres[tramo_top]} personas.",
                             f"Mayores de 45: {sum(1 for f in filas if f['edad'] >= 45)} registrados."]),
            seccion("Estado civil", grafico=grafico_civil, alto=240, detalle="estado_civil",
                    ayuda_detalle="Hacé clic en una barra para ver los registros.",
                    explicacion="Cantidad de registrados según el estado civil que declararon en el portal.",
                    lectura=[f"{civil[0][0]}: {formato_numero(civil[0][1])} registrados."]),
        ],
        "sugerencias": ["¿El perfil sirve para los pedidos que tenemos?", "¿Cómo atraer candidatos de más edad?"],
        "contexto_ia": {"total": total, "mujeres": sum(mujeres), "por_tramo": dict(zip(TRAMOS_ETIQ, map(sum, zip(mujeres, hombres)))),
                        "estado_civil": dict(civil)},
    }


# ==========================================================================
# 3. Ubicación
# ==========================================================================
@catalogo.registrar(
    "ubicacion", "Dónde viven",
    "Distribución de los registrados por departamento y por localidad.",
    icono="bi-geo-alt", **CON_PERIODO,
)
def ubicacion(periodo):
    filas = services.registros(periodo)
    total = len(filas)
    deptos = Counter(_depto(f) for f in filas).most_common()
    grafico_deptos = _barras_h("Registrados", [d for d, _ in deptos], [v for _, v in deptos], alto_barra=16)
    interior = sum(v for d, v in deptos if d not in ("Montevideo", "Canelones", "Sin dato"))

    locs = Counter(f"{f['localidad']} ({f['departamento']})" for f in filas if f["localidad"]).most_common(12)
    grafico_locs = _barras_h("Registrados", [l for l, _ in locs], [v for _, v in locs], g.SERIES[2])
    sin_dato = next((v for d, v in deptos if d == "Sin dato"), 0)

    return {
        "kpis": [
            {"label": "Registrados", "valor": formato_numero(total), "detalle": PERIODOS_WEB[periodo].lower()},
            {"label": "Montevideo", "valor": f"{_pct(dict(deptos).get('Montevideo', 0), total)}%", "detalle": "del total"},
            {"label": "Interior (sin Canelones)", "valor": f"{_pct(interior, total)}%", "detalle": f"{formato_numero(interior)} personas"},
            {"label": "Sin departamento", "valor": formato_numero(sin_dato), "alerta": sin_dato > 0,
             "detalle": "no completaron el dato"},
        ],
        "conclusiones": [
            f"Montevideo y Canelones concentran el {_pct(dict(deptos).get('Montevideo', 0) + dict(deptos).get('Canelones', 0), total)}% de los registrados.",
            f"El interior (sin Canelones) aporta {_pct(interior, total)}%: para pedidos fuera del área metropolitana la base es chica.",
            f"{locs[0][0]} es la localidad con más registrados." if locs else "",
            f"{formato_numero(sin_dato)} registros no tienen departamento: no aparecen en búsquedas por zona.",
        ],
        "secciones": [
            seccion("Registrados por departamento", grafico=grafico_deptos, alto=520, detalle="departamento",
                    ayuda_detalle="Hacé clic en un departamento para ver sus registrados.",
                    explicacion="Ranking de departamentos según la cantidad de registrados que viven en cada uno. "
                                "«Sin dato» son los que no completaron el departamento.",
                    lectura=[f"{deptos[0][0]} tiene {formato_numero(deptos[0][1])} registrados ({_pct(deptos[0][1], total)}%)."]),
            seccion("Localidades con más registrados", grafico=grafico_locs, alto=380, detalle="localidad",
                    ayuda_detalle="Hacé clic en una localidad para ver sus registrados.",
                    explicacion="Las 12 localidades con más registrados. Solo se cuentan los que completaron la localidad.",
                    lectura=["Sirve para decidir dónde publicar avisos zonales o abrir búsquedas por barrio."]),
        ],
        "sugerencias": ["¿Tenemos candidatos suficientes en Maldonado para la temporada?", "¿Dónde conviene publicar?"],
        "contexto_ia": {"total": total, "departamentos": dict(deptos), "localidades": dict(locs)},
    }


# ==========================================================================
# 4. Expectativa salarial
# ==========================================================================
@catalogo.registrar(
    "salarios", "Expectativa salarial",
    "Cuánto aspiran a ganar los registrados, cuánto ganan hoy y cómo cambia con la edad.",
    icono="bi-cash-coin", **CON_PERIODO,
)
def salarios(periodo):
    filas = [f for f in services.registros(periodo) if f["moneda"] == "UYU"]
    con_aspirado = [f for f in filas if f["salario_aspirado"] > 0]
    rangos = Counter(_rango(f["salario_aspirado"]) for f in con_aspirado)
    valores = [rangos[e] for e, _, _ in RANGOS_SALARIO]
    grafico_rangos = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        xAxis=g.eje_categorias([e for e, _, _ in RANGOS_SALARIO], axisLabel={"interval": 0, "rotate": 20, "color": g.TINTA_SUAVE}),
        yAxis=g.eje_valores(),
        series=[g.barras("Registrados", valores, g.SERIES[0], label={"show": True, "position": "top", "color": g.TINTA_SUAVE})],
    )
    med_asp = mediana([f["salario_aspirado"] for f in con_aspirado])
    empleados = [f for f in con_aspirado if f["salario_actual"] > 0]
    brecha = mediana([(f["salario_aspirado"] - f["salario_actual"]) / f["salario_actual"] * 100 for f in empleados])
    desempleados = sum(1 for f in filas if f["salario_actual"] == 0)

    actual_t, aspirado_t = [], []
    for t in TRAMOS_ETIQ:
        grupo = [f for f in empleados if _tramo(f["edad"]) == t]
        actual_t.append(round(mediana([f["salario_actual"] for f in grupo])) if grupo else None)
        aspirado_t.append(round(mediana([f["salario_aspirado"] for f in grupo])) if grupo else None)
    grafico_tramos = g.base(
        legend=g.leyenda(),
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pesos"},
        xAxis=g.eje_categorias(TRAMOS_ETIQ, name="Edad", nameLocation="middle", nameGap=28),
        yAxis=g.eje_valores("fmt:pesos_k"),
        grid={"left": 8, "right": 16, "top": 36, "bottom": 28, "containLabel": True},
        series=[g.barras("Gana hoy", actual_t, g.NEUTRO), g.barras("Aspira", aspirado_t, g.SERIES[0])],
    )

    return {
        "kpis": [
            {"label": "Aspiración mediana", "valor": formato_pesos(med_asp), "detalle": "salario nominal en pesos"},
            {"label": "Aspiran ganar más que hoy", "valor": formato_pct(brecha), "detalle": "mediana, entre quienes trabajan"},
            {"label": "Sin empleo actual", "valor": f"{_pct(desempleados, len(filas))}%", "detalle": f"{formato_numero(desempleados)} registrados"},
            {"label": "No indicaron aspiración", "valor": formato_numero(len(filas) - len(con_aspirado)),
             "detalle": "salario aspirado en 0"},
        ],
        "conclusiones": [
            f"La mitad de los registrados aspira a ganar más de {formato_pesos(med_asp)}.",
            f"Quienes trabajan aspiran, en la mediana, a un {formato_pct(brecha)} más de lo que ganan hoy.",
            f"{_pct(desempleados, len(filas))}% no tiene empleo actual: suelen aceptar antes las propuestas.",
            "La aspiración sube con la edad: para puestos de entrada conviene apuntar a los tramos más jóvenes.",
        ],
        "secciones": [
            seccion("Cuánto aspiran a ganar", grafico=grafico_rangos, alto=320, detalle="rango_salario",
                    ayuda_detalle="Hacé clic en un rango para ver quiénes aspiran a ese salario.",
                    explicacion="Cantidad de registrados según el salario mensual que dicen aspirar, en pesos. "
                                "No incluye a quienes lo indicaron en dólares ni a quienes lo dejaron vacío.",
                    lectura=[f"El rango más frecuente es {max(rangos, key=rangos.get)}."]),
            seccion("Lo que ganan hoy y lo que aspiran, por edad", grafico=grafico_tramos, alto=320, detalle="tramo_salario",
                    ayuda_detalle="Hacé clic en un tramo para ver los registros de esa edad.",
                    explicacion="Para cada tramo de edad, la barra gris es el salario actual típico (mediana) y la azul "
                                "el aspirado. Solo se cuentan quienes hoy tienen empleo. La diferencia entre las dos "
                                "barras es lo que esperan mejorar al cambiar de trabajo.",
                    lectura=["Comparar con el salario que ofrece el cliente ayuda a anticipar rechazos de propuestas."]),
        ],
        "sugerencias": ["¿Nuestros pedidos pagan lo que aspiran los candidatos?", "¿Qué tramo acepta salarios de entrada?"],
        "contexto_ia": {"mediana_aspirado": med_asp, "brecha_mediana_pct": round(brecha, 1),
                        "por_rango": dict(rangos), "sin_empleo": desempleados},
    }


# ==========================================================================
# 5. Disponibilidad y requisitos
# ==========================================================================
@catalogo.registrar(
    "disponibilidad", "Disponibilidad y requisitos",
    "Qué parte de la base acepta horario rotativo, zafrales, horario completo y tiene libreta de conducir.",
    icono="bi-calendar-week", **CON_PERIODO,
)
def disponibilidad(periodo):
    filas = services.registros(periodo)
    total = len(filas)
    pct = {nombre: _pct(sum(f[campo] == SI for f in filas), total) for nombre, campo in ATRIBUTOS.items()}
    grafico_atrib = _barras_h("Cumplen", list(pct), list(pct.values()), formato="{c}%")
    grafico_atrib["xAxis"]["max"] = 100
    grafico_atrib["xAxis"]["axisLabel"]["formatter"] = "fmt:pct"
    grafico_atrib["tooltip"]["valueFormatter"] = "fmt:pct"

    req = Counter(_requisitos(f) for f in filas)
    etiquetas = [f"{n} de 4" for n in range(5)]
    grafico_req = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        xAxis=g.eje_categorias(etiquetas, name="Requisitos que cumple", nameLocation="middle", nameGap=28),
        yAxis=g.eje_valores(),
        grid={"left": 8, "right": 16, "top": 24, "bottom": 28, "containLabel": True},
        series=[g.barras("Registrados", [{"value": req[n], "itemStyle": {"color": g.AZUL[min(n + 2, 6)]}} for n in range(5)],
                         label={"show": True, "position": "top", "color": g.TINTA_SUAVE})],
    )
    flexibles = req[3] + req[4]

    return {
        "kpis": [
            {"label": "Horario rotativo", "valor": f"{pct['Horario rotativo']}%", "detalle": "lo aceptan"},
            {"label": "Zafrales", "valor": f"{pct['Acepta zafrales']}%", "detalle": "aceptan trabajos por temporada"},
            {"label": "Libreta de conducir", "valor": f"{pct['Libreta de conducir']}%", "detalle": "tienen libreta"},
            {"label": "Perfil flexible", "valor": formato_numero(flexibles), "detalle": "cumplen 3 o 4 requisitos"},
        ],
        "conclusiones": [
            f"Solo {pct['Libreta de conducir']}% tiene libreta: explica por qué cuesta cubrir los pedidos de chofer.",
            f"{pct['Horario rotativo']}% acepta horario rotativo, clave para retail y call center.",
            f"{formato_numero(flexibles)} registrados cumplen 3 o 4 requisitos: son la reserva para pedidos urgentes.",
            "Filtrar por estos campos antes de llamar ahorra entrevistas que terminan en «no puedo ese horario».",
        ],
        "secciones": [
            seccion("Qué aceptan y qué tienen", grafico=grafico_atrib, alto=240, detalle="atributo",
                    ayuda_detalle="Hacé clic en una barra para ver quiénes cumplen ese requisito.",
                    explicacion="Porcentaje de registrados que marcaron cada condición en el portal. "
                                "Cada barra es independiente: una persona puede cumplir varias.",
                    lectura=[f"Horario completo: {pct['Horario completo']}%. Zafrales: {pct['Acepta zafrales']}%."]),
            seccion("Cuántos requisitos cumple cada persona", grafico=grafico_req, alto=300, detalle="requisitos",
                    ayuda_detalle="Hacé clic en una barra para ver esas personas.",
                    explicacion="Cuenta cuántas de las cuatro condiciones (horario completo, rotativo, zafrales y libreta) "
                                "cumple cada registrado. Más a la derecha, perfil más flexible.",
                    lectura=[f"{req[0]} registrados no cumplen ninguna condición."],
                    acciones=[{"prioridad": "media", "titulo": "Armar una reserva de perfiles flexibles",
                               "detalle": f"Los {formato_numero(flexibles)} registrados con 3 o 4 requisitos son los primeros "
                                          "a llamar cuando entra un pedido urgente o de temporada."}]),
        ],
        "sugerencias": ["¿Cuántos choferes potenciales tenemos?", "¿A quién llamo para un pedido de zafra?"],
        "contexto_ia": {"porcentajes": pct, "por_requisitos": dict(req)},
    }


# ==========================================================================
# 6. Calidad de los datos
# ==========================================================================
@catalogo.registrar(
    "calidad", "Calidad de los datos",
    "Qué tan completos están los registros y a quiénes hay que pedirles que completen su perfil.",
    icono="bi-clipboard-data", **FOTO,
)
def calidad(periodo):
    filas = services.registros()
    total = len(filas)
    completo = {c: _pct(sum(fn(f) for f in filas), total) for c, fn in CAMPOS.items()}
    orden = sorted(completo.items(), key=lambda x: x[1])
    grafico = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        grid={"left": 8, "right": 56, "top": 8, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores("fmt:pct", max=100),
        yAxis=g.eje_categorias([c for c, _ in orden]),
        series=[{
            "name": "Completo", "type": "bar", "barMaxWidth": 22,
            "data": [{"value": v, "itemStyle": {"color": g.ESTADO["bien"] if v >= 90 else g.ESTADO["serio"] if v >= 60 else g.ESTADO["critico"],
                                                "borderRadius": [0, 4, 4, 0]}} for _, v in orden],
            "label": {"show": True, "position": "right", "formatter": "{c}%", "color": g.TINTA_SUAVE},
        }],
    )
    perfil_completo = sum(all(fn(f) for fn in CAMPOS.values()) for f in filas)
    sin_contacto = sum(1 for f in filas if not f["email"] and not f["celular"])

    return {
        "kpis": [
            {"label": "Perfiles completos", "valor": f"{_pct(perfil_completo, total)}%",
             "detalle": f"{formato_numero(perfil_completo)} tienen los 6 datos"},
            {"label": "Con CV adjunto", "valor": f"{completo['CV adjunto']}%", "alerta": completo["CV adjunto"] < 60,
             "detalle": "del total"},
            {"label": "Sin forma de contacto", "valor": formato_numero(sin_contacto), "alerta": sin_contacto > 0,
             "detalle": "ni email ni celular"},
            {"label": "Dato más incompleto", "valor": orden[0][0], "detalle": f"{orden[0][1]}% lo tiene"},
        ],
        "conclusiones": [
            f"Solo {_pct(perfil_completo, total)}% de los registros tiene todos los datos clave.",
            f"El CV es lo que más falta: solo {completo['CV adjunto']}% lo adjuntó.",
            f"{formato_numero(sin_contacto)} registros no tienen ni email ni celular: no se los puede contactar.",
            "Los registros completos avanzan más en el proceso (ver «De registro web a ingreso»).",
        ],
        "secciones": [
            seccion("Qué tan completo está cada dato", grafico=grafico, alto=300, detalle="faltante",
                    ayuda_detalle="Hacé clic en una barra para ver los registros a los que les falta ese dato.",
                    explicacion="Porcentaje de registros que tienen cada dato cargado. Verde: 90% o más; naranja: entre "
                                "60% y 90%; rojo: menos de 60%. Al hacer clic se listan los que no lo tienen.",
                    lectura=[f"{orden[0][0]} es el dato con menos carga ({orden[0][1]}%)."],
                    acciones=[
                        {"prioridad": "alta", "titulo": "Pedir el CV a los registros activos",
                         "detalle": "Enviar un recordatorio a quienes actualizaron en el último año y no tienen CV: es lo que "
                                    "más demora la preselección."},
                        {"prioridad": "media", "titulo": "Hacer obligatorios los datos clave en el portal",
                         "detalle": "Email o celular y departamento deberían ser obligatorios al registrarse."},
                    ]),
        ],
        "sugerencias": ["¿Qué datos conviene hacer obligatorios?", "Redactame el email para pedir el CV"],
        "contexto_ia": {"completitud": completo, "perfiles_completos": perfil_completo, "sin_contacto": sin_contacto},
    }


# ==========================================================================
# 7. De registro web a ingreso
# ==========================================================================
@catalogo.registrar(
    "conversion", "De registro web a ingreso",
    "Cuántos registrados pasan a candidato, se entrevistan e ingresan, y qué perfiles avanzan más.",
    icono="bi-funnel", **CON_PERIODO,
)
def conversion(periodo):
    filas = services.registros(periodo)
    conteo = [sum(1 for f in filas if f["etapa"] >= i) for i in range(len(ETAPAS))]
    grafico_embudo = g.base(
        tooltip={"trigger": "item", "confine": True, "formatter": "{b}: {c}"},
        series=[{
            "type": "funnel", "sort": "none", "gap": 4, "left": "8%", "width": "84%", "top": 10, "bottom": 10, "minSize": "14%",
            "label": {"show": True, "position": "inside", "formatter": "{b}\n{c}", "color": "#fff", "fontWeight": 600, "lineHeight": 18},
            "itemStyle": {"borderColor": "#fff", "borderWidth": 0, "borderRadius": 6},
            "data": [{"name": n, "value": v, "itemStyle": {"color": c}}
                     for n, v, c in zip(ETAPAS, conteo, [g.AZUL[6], g.AZUL[5], g.AZUL[4], g.AZUL[3]])],
        }],
    )

    # Qué perfiles avanzan más: % que llega a entrevista según completitud
    grupos = {"Perfil completo": lambda f: f["cv"] and f["salario_aspirado"] > 0 and f["departamento"],
              "Sin CV": lambda f: not f["cv"],
              "Sin departamento": lambda f: not f["departamento"],
              "Actualizado en el último año": lambda f: f["dias_act"] <= 365,
              "Sin actualizar hace más de 1 año": lambda f: f["dias_act"] > 365}
    tasas = {n: _pct(sum(f["etapa"] >= 2 for f in filas if fn(f)), sum(1 for f in filas if fn(f))) for n, fn in grupos.items()}
    media = _pct(conteo[2], conteo[0])
    grafico_grupos = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        grid={"left": 8, "right": 56, "top": 8, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores("fmt:pct"),
        yAxis=g.eje_categorias(list(tasas), inverse=True),
        series=[{"name": "Llega a entrevista", "type": "bar", "barMaxWidth": 22,
                 "data": [{"value": v, "itemStyle": {"color": g.POSITIVO if v >= media else g.NEGATIVO,
                                                     "borderRadius": [0, 4, 4, 0]}} for v in tasas.values()],
                 "label": {"show": True, "position": "right", "formatter": "{c}%", "color": g.TINTA_SUAVE},
                 "markLine": {"silent": True, "symbol": "none", "lineStyle": {"color": g.TINTA_SUAVE, "type": "dashed"},
                              "label": {"formatter": f"media {media}%", "color": g.TINTA_SUAVE}, "data": [{"xAxis": media}]}}],
    )

    return {
        "kpis": [
            {"label": "Registrados", "valor": formato_numero(conteo[0]), "detalle": PERIODOS_WEB[periodo].lower()},
            {"label": "Pasaron a candidato", "valor": f"{_pct(conteo[1], conteo[0])}%", "detalle": formato_numero(conteo[1])},
            {"label": "Entrevistados", "valor": f"{_pct(conteo[2], conteo[0])}%", "detalle": formato_numero(conteo[2])},
            {"label": "Ingresaron", "valor": f"{_pct(conteo[3], conteo[0])}%", "detalle": formato_numero(conteo[3])},
        ],
        "conclusiones": [
            f"De cada 100 registrados en el portal, {_pct(conteo[1], conteo[0])} pasan a candidato y {_pct(conteo[3], conteo[0])} ingresan.",
            f"La mayor pérdida es entre el registro y pasar a candidato: {formato_numero(conteo[0] - conteo[1])} registros nunca se gestionaron.",
            f"Con perfil completo llega a entrevista el {tasas['Perfil completo']}%; sin CV, el {tasas['Sin CV']}%.",
            "Completar datos y mantener la base actualizada mejora directamente la conversión.",
        ],
        "secciones": [
            seccion("Cómo avanzan los registrados", grafico=grafico_embudo, alto=320, detalle="etapa",
                    ayuda_detalle="Hacé clic en una etapa para ver quiénes llegaron hasta ahí.",
                    explicacion="Embudo desde el registro en el portal hasta el ingreso. Cada franja cuenta a quienes "
                                "llegaron al menos a esa etapa. «Pasó a candidato» significa que tiene ficha en la "
                                "tabla Candidatos.",
                    lectura=[f"{_pct(conteo[2], conteo[1])}% de los que pasan a candidato llega a entrevistarse.",
                             f"{_pct(conteo[3], conteo[2])}% de los entrevistados ingresa."]),
            seccion("Qué perfiles avanzan más", grafico=grafico_grupos, alto=280, detalle="grupo",
                    ayuda_detalle="Hacé clic en una barra para ver los registros de ese grupo.",
                    explicacion="Porcentaje de cada grupo que llegó a entrevista. En azul los grupos por encima de la "
                                "media y en rojo los que están por debajo. La línea punteada es la media.",
                    lectura=["Los grupos se superponen: una persona puede estar sin CV y sin actualizar a la vez."]),
        ],
        "sugerencias": ["¿Por qué tantos registros no pasan a candidato?", "¿Cuánto mejora la conversión con CV?"],
        "contexto_ia": {"embudo": dict(zip(ETAPAS, conteo)), "llega_a_entrevista_por_grupo": tasas},
    }


# ==========================================================================
# 8. Registrados sin gestionar
# ==========================================================================
def _sin_gestion(f):
    """Activos y con buen perfil, pero nunca pasaron a candidato."""
    return f["etapa"] == 0 and f["dias_act"] <= 180 and f["cv"] and (f["email"] or f["celular"])


@catalogo.registrar(
    "sin-gestionar", "Registrados sin gestionar",
    "Personas activas y con buen perfil que nunca fueron contactadas: la oportunidad más rápida para cubrir pedidos.",
    icono="bi-person-exclamation", **FOTO,
)
def sin_gestionar(periodo):
    filas = services.registros()
    pendientes = [f for f in filas if _sin_gestion(f)]
    deptos = Counter(_depto(f) for f in pendientes).most_common()
    grafico = _barras_h("Sin gestionar", [d for d, _ in deptos], [v for _, v in deptos], g.SERIES[1], alto_barra=16)
    flexibles = [f for f in pendientes if _requisitos(f) >= 3]
    jovenes = [f for f in pendientes if f["edad"] < 30]
    recientes = [f for f in pendientes if f["dias_act"] <= 30]

    return {
        "kpis": [
            {"label": "Sin gestionar", "valor": formato_numero(len(pendientes)), "alerta": bool(pendientes),
             "detalle": "activos, con CV y contacto"},
            {"label": "Actualizados este mes", "valor": formato_numero(len(recientes)), "detalle": "los más calientes"},
            {"label": "Perfil flexible", "valor": formato_numero(len(flexibles)), "detalle": "3 o 4 requisitos"},
            {"label": "Menores de 30", "valor": formato_numero(len(jovenes)), "detalle": "aptos para puestos de entrada"},
        ],
        "conclusiones": [
            f"Hay {formato_numero(len(pendientes))} personas activas, con CV y forma de contacto que nunca pasaron a candidato.",
            f"{formato_numero(len(recientes))} actualizaron su perfil en el último mes: hay que llamarlas primero.",
            f"{deptos[0][0]} concentra {_pct(deptos[0][1], len(pendientes))}% de los pendientes." if deptos else "",
            "Contactarlos es más rápido y barato que publicar un aviso nuevo.",
        ],
        "secciones": [
            seccion("Dónde están los registrados sin gestionar", grafico=grafico, alto=480, detalle="sin_gestion",
                    ayuda_detalle="Hacé clic en un departamento para ver la lista de personas a contactar.",
                    explicacion="Personas que actualizaron su registro en los últimos 6 meses, tienen CV y email o "
                                "celular, pero nunca tuvieron ficha de candidato. Agrupadas por departamento.",
                    lectura=["Al abrir el detalle se puede exportar la lista a Excel para repartirla entre los selectores."],
                    acciones=[
                        {"prioridad": "alta", "titulo": f"Llamar a los {len(recientes)} actualizados este mes",
                         "detalle": "Están buscando trabajo ahora. Contactarlos esta semana y cruzarlos con los pedidos abiertos."},
                        {"prioridad": "media", "titulo": f"Pasar a candidato a los {len(flexibles)} de perfil flexible",
                         "detalle": "Cumplen 3 o 4 requisitos: son ideales para pedidos urgentes o de temporada."},
                        {"prioridad": "baja", "titulo": "Revisar este listado todas las semanas",
                         "detalle": "Asignar un responsable para que ningún registro activo quede más de 30 días sin gestionar."},
                    ]),
        ],
        "sugerencias": ["¿A quién llamo primero?", "¿Cuántos sirven para los pedidos abiertos de cajero?"],
        "contexto_ia": {"sin_gestionar": len(pendientes), "por_departamento": dict(deptos),
                        "flexibles": len(flexibles), "actualizados_mes": len(recientes)},
    }


# ==========================================================================
# 9-12. Análisis del CV (experiencia, permanencia, formación, idiomas)
# ==========================================================================
BUCKETS_EXP = [("Sin experiencia", 0, 0), ("Menos de 1 año", 0.01, 0.99), ("1 a 3 años", 1, 2.99),
               ("3 a 5 años", 3, 4.99), ("5 a 10 años", 5, 9.99), ("Más de 10 años", 10, 999)]
BUCKETS_PERM = [("Menos de 3 meses", 0, 2), ("3 a 6 meses", 3, 5), ("6 a 12 meses", 6, 11),
                ("1 a 2 años", 12, 23), ("2 a 5 años", 24, 59), ("Más de 5 años", 60, 9999)]


def _bucket_exp(anios):
    for etiq, a, b in BUCKETS_EXP:
        if a <= anios <= b:
            return etiq
    return BUCKETS_EXP[-1][0]


def _bucket_perm(meses):
    for etiq, a, b in BUCKETS_PERM:
        if a <= meses <= b:
            return etiq
    return BUCKETS_PERM[-1][0]


def _tasa_ingreso(filas):
    return _pct(sum(f["etapa"] == 3 for f in filas), len(filas))


def _barras_v(nombre, etiquetas, valores, colores=None, formato="{c}", rotar=0):
    datos = [{"value": v, "itemStyle": {"color": c}} for v, c in zip(valores, colores)] if colores else valores
    return g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        xAxis=g.eje_categorias(etiquetas, axisLabel={"interval": 0, "rotate": rotar, "color": g.TINTA_SUAVE}),
        yAxis=g.eje_valores(),
        series=[g.barras(nombre, datos, g.SERIES[0], label={"show": True, "position": "top",
                                                             "formatter": formato, "color": g.TINTA_SUAVE})],
    )


@catalogo.registrar(
    "experiencia", "Experiencia laboral",
    "Cuántos años de experiencia declaran, en qué cargos trabajaron y cuánto pesa la experiencia para ingresar.",
    icono="bi-briefcase", **CON_PERIODO,
)
def experiencia_laboral(periodo):
    filas = services.registros(periodo)
    perfil = cv.perfil_cv()
    ids = {f["id"] for f in filas}
    total = len(filas)

    por_bucket = Counter(_bucket_exp(perfil[f["id"]]["anios_exp"]) for f in filas)
    etiq_b = [e for e, _, _ in BUCKETS_EXP]
    grafico_anios = _barras_v("Registrados", etiq_b, [por_bucket[e] for e in etiq_b],
                              [g.NEUTRO] + [g.AZUL[i] for i in (1, 2, 3, 4, 5)], rotar=15)

    cargos = Counter()
    for e in cv.experiencia():
        if e["web_user_id"] in ids:
            cargos[e["cargo"]] += 1
    top_cargos = cargos.most_common(12)
    grafico_cargos = _barras_h("Personas", [c for c, _ in top_cargos], [v for _, v in top_cargos], g.SERIES[2])

    tasas = [_tasa_ingreso([f for f in filas if _bucket_exp(perfil[f["id"]]["anios_exp"]) == e]) for e in etiq_b]
    media = _tasa_ingreso(filas)
    grafico_tasa = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        xAxis=g.eje_categorias(etiq_b, axisLabel={"interval": 0, "rotate": 15, "color": g.TINTA_SUAVE}),
        yAxis=g.eje_valores("fmt:pct"),
        series=[{"name": "Ingresaron", "type": "bar", "barMaxWidth": 36,
                 "data": [{"value": v, "itemStyle": {"color": g.POSITIVO if v >= media else g.NEGATIVO,
                                                     "borderRadius": [4, 4, 0, 0]}} for v in tasas],
                 "label": {"show": True, "position": "top", "formatter": "{c}%", "color": g.TINTA_SUAVE},
                 "markLine": {"silent": True, "symbol": "none", "lineStyle": {"color": g.TINTA_SUAVE, "type": "dashed"},
                              "label": {"formatter": f"media {media}%", "color": g.TINTA_SUAVE}, "data": [{"yAxis": media}]}}],
    )
    con_exp = [f for f in filas if perfil[f["id"]]["trabajos"] > 0]
    trabajando = sum(1 for e in cv.experiencia() if e["web_user_id"] in ids and e["actual"] == cv.TRABAJO_ACTUAL_SI)
    sin_exp = por_bucket["Sin experiencia"]
    mejor = etiq_b[tasas.index(max(tasas))]

    return {
        "kpis": [
            {"label": "Con experiencia", "valor": f"{_pct(len(con_exp), total)}%", "detalle": f"{formato_numero(len(con_exp))} personas"},
            {"label": "Experiencia mediana",
             "valor": f"{mediana([perfil[f['id']]['anios_exp'] for f in con_exp]):.1f} años".replace(".", ",") if con_exp else "—",
             "detalle": "entre quienes declaran trabajos"},
            {"label": "Trabajando hoy", "valor": f"{_pct(trabajando, total)}%", "detalle": "según su CV"},
            {"label": "Cargo más declarado", "valor": top_cargos[0][0] if top_cargos else "—",
             "detalle": f"{top_cargos[0][1]} personas" if top_cargos else ""},
        ],
        "conclusiones": [
            f"{_pct(sin_exp, total)}% no declara experiencia laboral: son perfiles para puestos de entrada.",
            f"Los cargos más comunes son {', '.join(c.lower() for c, _ in top_cargos[:3])}: coinciden con los puestos más pedidos.",
            f"Ingresan más los que tienen {mejor.lower()} ({max(tasas)}%) que los que no tienen experiencia ({tasas[0]}%).",
            "Cruzar el cargo declarado con el puesto del pedido es el filtro más rápido para preseleccionar.",
        ],
        "secciones": [
            seccion("Años de experiencia", grafico=grafico_anios, alto=300, detalle="anios_exp",
                    ayuda_detalle="Hacé clic en una barra para ver las personas de ese grupo.",
                    explicacion="Suma la duración de todos los trabajos que cada persona cargó en su CV y los agrupa por "
                                "años. La barra gris son quienes no cargaron ningún trabajo.",
                    lectura=[f"{formato_numero(sin_exp)} registrados no tienen experiencia cargada."]),
            seccion("En qué cargos trabajaron", grafico=grafico_cargos, alto=380, detalle="cargo",
                    ayuda_detalle="Hacé clic en un cargo para ver quiénes lo tuvieron.",
                    explicacion="Cantidad de personas que declararon haber trabajado en cada cargo (los 12 más frecuentes). "
                                "Una persona con varios trabajos puede sumar en más de un cargo.",
                    lectura=[f"{top_cargos[0][0]} es el cargo con más experiencia declarada." if top_cargos else ""]),
            seccion("Cuánto pesa la experiencia para ingresar", grafico=grafico_tasa, alto=300, detalle="anios_exp",
                    ayuda_detalle="Hacé clic en una barra para ver las personas de ese grupo.",
                    explicacion="Para cada grupo de experiencia, qué porcentaje terminó ingresando a trabajar por Manpower. "
                                "En azul los grupos por encima de la media y en rojo los que están por debajo.",
                    lectura=["La experiencia mejora las chances de ingresar, sobre todo a partir del primer año."]),
        ],
        "sugerencias": ["¿Cuántos tienen experiencia como cajero?", "¿Conviene presentar candidatos sin experiencia?"],
        "contexto_ia": {"por_anios": dict(por_bucket), "cargos": dict(top_cargos), "ingreso_por_anios": dict(zip(etiq_b, tasas))},
    }


@catalogo.registrar(
    "permanencia", "Permanencia y motivos de salida",
    "Cuánto duran en cada trabajo, por qué se fueron y en qué cargos la rotación es más alta.",
    icono="bi-hourglass-split", **FOTO,
)
def permanencia(periodo):
    trabajos = [e for e in cv.experiencia() if e["actual"] != cv.TRABAJO_ACTUAL_SI]
    por_bucket = Counter(_bucket_perm(e["meses"]) for e in trabajos)
    etiq = [e for e, _, _ in BUCKETS_PERM]
    grafico_perm = _barras_v("Trabajos", etiq, [por_bucket[e] for e in etiq],
                             [g.NARANJA[4], g.NARANJA[3], g.NARANJA[2], g.AZUL[2], g.AZUL[4], g.AZUL[6]], rotar=15)

    causales = Counter(e["causal"] for e in trabajos if e["causal"]).most_common()
    grafico_causas = _barras_h("Salidas", [c for c, _ in causales], [v for _, v in causales], g.SERIES[1])

    por_cargo = {}
    for e in trabajos:
        por_cargo.setdefault(e["cargo"], []).append(e["meses"])
    cargos = sorted(((c, round(mediana(m))) for c, m in por_cargo.items() if len(m) >= 20), key=lambda x: x[1])
    grafico_cargos = _barras_h("Meses (mediana)", [c for c, _ in cargos], [v for _, v in cargos], g.SERIES[0],
                               formato="{c} m")
    cortos = sum(por_bucket[e] for e in etiq[:2])
    zafra = dict(causales).get("Fin de contrato / zafra", 0)
    largos_por_persona = Counter(e["web_user_id"] for e in cv.experiencia() if e["meses"] >= 24)
    estables = len(largos_por_persona)

    return {
        "kpis": [
            {"label": "Permanencia mediana", "valor": f"{round(mediana([e['meses'] for e in trabajos]))} meses",
             "detalle": "por trabajo terminado"},
            {"label": "Duraron menos de 6 meses", "valor": f"{_pct(cortos, len(trabajos))}%", "alerta": _pct(cortos, len(trabajos)) > 30,
             "detalle": f"{formato_numero(cortos)} trabajos"},
            {"label": "Motivo más común", "valor": causales[0][0] if causales else "—",
             "detalle": f"{_pct(causales[0][1], len(trabajos))}% de las salidas" if causales else ""},
            {"label": "Perfiles estables", "valor": formato_numero(estables), "detalle": "con algún trabajo de 2 años o más"},
        ],
        "conclusiones": [
            f"La mitad de los trabajos declarados duró menos de {round(mediana([e['meses'] for e in trabajos]))} meses.",
            f"«{causales[0][0]}» explica el {_pct(causales[0][1], len(trabajos))}% de las salidas." if causales else "",
            f"{cargos[0][0]} es el cargo con menor permanencia ({cargos[0][1]} meses) y {cargos[-1][0]} el de mayor ({cargos[-1][1]} meses)." if cargos else "",
            f"Hay {formato_numero(estables)} personas con algún trabajo de 2 años o más: ideales para puestos que buscan estabilidad.",
        ],
        "secciones": [
            seccion("Cuánto duran en cada trabajo", grafico=grafico_perm, alto=300, detalle="permanencia",
                    ayuda_detalle="Hacé clic en una barra para ver quiénes tuvieron trabajos de esa duración.",
                    explicacion="Cada trabajo terminado que figura en los CV, agrupado por cuánto duró. En naranja las "
                                "permanencias cortas (menos de un año) y en azul las largas. El trabajo actual no se cuenta "
                                "porque todavía no terminó.",
                    lectura=[f"{formato_numero(cortos)} trabajos duraron menos de 6 meses."]),
            seccion("Por qué se fueron", grafico=grafico_causas, alto=300, detalle="causal",
                    ayuda_detalle="Hacé clic en un motivo para ver quiénes salieron por esa razón.",
                    explicacion="Motivo de salida declarado en cada trabajo terminado (campo causal de baja del CV).",
                    lectura=[f"{formato_numero(zafra)} salidas fueron por fin de contrato o zafra: personas acostumbradas a trabajos temporales."],
                    acciones=[
                        {"prioridad": "media", "titulo": "Usar a los zafrales para pedidos de temporada",
                         "detalle": f"{formato_numero(zafra)} salidas fueron por fin de zafra o contrato: ya conocen la modalidad "
                                    "y suelen aceptar trabajos temporales."},
                        {"prioridad": "baja", "titulo": "Preguntar por la renuncia por mejor oferta",
                         "detalle": "Es el motivo más común: en la entrevista conviene validar salario y condiciones para "
                                    "evitar que se vayan rápido de la asignación."},
                    ]),
            seccion("Permanencia por cargo", grafico=grafico_cargos, alto=380, detalle="cargo",
                    ayuda_detalle="Hacé clic en un cargo para ver quiénes lo tuvieron.",
                    explicacion="Duración típica (mediana, en meses) de los trabajos de cada cargo. Solo se muestran cargos "
                                "con al menos 20 trabajos declarados. Más corta la barra, más rotación.",
                    lectura=["Los cargos con baja permanencia necesitan más reposición: conviene tener reserva de candidatos."]),
        ],
        "sugerencias": ["¿Qué cargos rotan más?", "¿Cómo reducir las salidas por mejor oferta?"],
        "contexto_ia": {"por_duracion": dict(por_bucket), "causales": dict(causales), "permanencia_por_cargo": dict(cargos)},
    }


@catalogo.registrar(
    "formacion", "Formación",
    "Máximo nivel educativo, si lo terminaron, qué estudiaron y cuánto influye la formación en el ingreso.",
    icono="bi-mortarboard", **CON_PERIODO,
)
def formacion(periodo):
    filas = services.registros(periodo)
    perfil = cv.perfil_cv()
    ids = {f["id"] for f in filas}
    total = len(filas)
    niveles = cv.NIVELES_EDUCATIVOS

    completos = [sum(1 for f in filas if perfil[f["id"]]["nivel_max"] == n and perfil[f["id"]]["nivel_completo"]) for n in niveles]
    incompletos = [sum(1 for f in filas if perfil[f["id"]]["nivel_max"] == n and not perfil[f["id"]]["nivel_completo"]) for n in niveles]
    grafico_nivel = g.base(
        legend=g.leyenda(data=["Completo", "Incompleto"]),
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        xAxis=g.eje_categorias(niveles, axisLabel={"interval": 0, "rotate": 15, "color": g.TINTA_SUAVE}),
        yAxis=g.eje_valores(),
        series=[{"name": "Completo", "type": "bar", "stack": "n", "barMaxWidth": 40, "data": completos,
                 "itemStyle": {"color": g.SERIES[0]}},
                {"name": "Incompleto", "type": "bar", "stack": "n", "data": incompletos,
                 "itemStyle": {"color": g.AZUL[1], "borderRadius": [4, 4, 0, 0]}}],
    )

    cursos = Counter()
    for fm in cv.formacion():
        if fm["web_user_id"] in ids and fm["nivel_orden"] >= 3:
            cursos[fm["curso"]] += 1
    top = cursos.most_common(12)
    grafico_cursos = _barras_h("Personas", [c for c, _ in top], [v for _, v in top], g.SERIES[6])

    tasas = [_tasa_ingreso([f for f in filas if perfil[f["id"]]["nivel_max"] == n]) for n in niveles]
    media = _tasa_ingreso(filas)
    grafico_tasa = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        xAxis=g.eje_categorias(niveles, axisLabel={"interval": 0, "rotate": 15, "color": g.TINTA_SUAVE}),
        yAxis=g.eje_valores("fmt:pct"),
        series=[{"name": "Ingresaron", "type": "bar", "barMaxWidth": 36,
                 "data": [{"value": v, "itemStyle": {"color": g.POSITIVO if v >= media else g.NEGATIVO,
                                                     "borderRadius": [4, 4, 0, 0]}} for v in tasas],
                 "label": {"show": True, "position": "top", "formatter": "{c}%", "color": g.TINTA_SUAVE},
                 "markLine": {"silent": True, "symbol": "none", "lineStyle": {"color": g.TINTA_SUAVE, "type": "dashed"},
                              "label": {"formatter": f"media {media}%", "color": g.TINTA_SUAVE}, "data": [{"yAxis": media}]}}],
    )
    con_terciaria = sum(completos[i] + incompletos[i] for i in range(4, len(niveles)))
    bachiller_completo = sum(completos[i] for i in range(2, len(niveles)))
    mas_comun = niveles[max(range(len(niveles)), key=lambda i: completos[i] + incompletos[i])]
    incompletos_tot = sum(incompletos)

    return {
        "kpis": [
            {"label": "Nivel más común", "valor": mas_comun, "detalle": "máximo nivel alcanzado"},
            {"label": "Bachillerato completo o más", "valor": f"{_pct(bachiller_completo, total)}%", "detalle": f"{formato_numero(bachiller_completo)} personas"},
            {"label": "Formación terciaria", "valor": f"{_pct(con_terciaria, total)}%", "detalle": "terciario, universitario o posgrado"},
            {"label": "Último nivel sin terminar", "valor": f"{_pct(incompletos_tot, total)}%", "detalle": "lo están cursando o lo dejaron"},
        ],
        "conclusiones": [
            f"El nivel más frecuente es {mas_comun.lower()}; {_pct(con_terciaria, total)}% tiene formación terciaria.",
            f"{_pct(incompletos_tot, total)}% no terminó su último nivel: muchos estudian y buscan horarios compatibles.",
            f"Los que más ingresan son los de nivel {niveles[tasas.index(max(tasas))].lower()} ({max(tasas)}%).",
            f"{top[0][0]} es la formación técnica o terciaria más común." if top else "",
        ],
        "secciones": [
            seccion("Máximo nivel educativo", grafico=grafico_nivel, alto=320, detalle="nivel",
                    ayuda_detalle="Hacé clic en una barra para ver las personas de ese nivel (completo o incompleto).",
                    explicacion="Para cada persona se toma el nivel más alto que cargó en el CV. La parte oscura de la barra "
                                "son quienes lo terminaron y la clara quienes lo dejaron o lo están cursando.",
                    lectura=[f"{formato_numero(completos[2] + incompletos[2])} personas llegaron hasta bachillerato."]),
            seccion("Qué estudiaron", grafico=grafico_cursos, alto=380, detalle="curso",
                    ayuda_detalle="Hacé clic en una formación para ver quiénes la tienen.",
                    explicacion="Las 12 formaciones técnicas, terciarias o universitarias más frecuentes (de la tabla de "
                                "cursos y carreras).",
                    lectura=["Útil para pedidos que piden una formación específica (administración, logística, informática)."]),
            seccion("Cuánto influye la formación en el ingreso", grafico=grafico_tasa, alto=300, detalle="nivel",
                    ayuda_detalle="Hacé clic en una barra para ver las personas de ese nivel.",
                    explicacion="Porcentaje de cada nivel educativo que terminó ingresando. En azul los niveles por encima "
                                "de la media y en rojo los que están por debajo.",
                    lectura=["Para muchos puestos operativos un nivel alto no garantiza ingresar: pesan más la experiencia y la disponibilidad."]),
        ],
        "sugerencias": ["¿Cuántos tienen formación en logística?", "¿Los estudiantes aceptan horario rotativo?"],
        "contexto_ia": {"por_nivel": dict(zip(niveles, map(sum, zip(completos, incompletos)))),
                        "ingreso_por_nivel": dict(zip(niveles, tasas)), "formaciones": dict(top)},
    }


@catalogo.registrar(
    "idiomas", "Idiomas",
    "Qué idiomas declaran, con qué nivel y cuántos sirven para puestos bilingües.",
    icono="bi-translate", **CON_PERIODO,
)
def idiomas(periodo):
    filas = services.registros(periodo)
    ids = {f["id"] for f in filas}
    total = len(filas)
    decl = [i for i in cv.idiomas() if i["web_user_id"] in ids]
    lista = [k for k, _ in Counter(i["idioma"] for i in decl).most_common()]
    colores = [g.AZUL[1], g.AZUL[3], g.AZUL[5], g.SERIES[1]]
    grafico_idiomas = g.base(
        legend=g.leyenda(data=list(cv.NIVELES_IDIOMA.values())),
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        grid={"left": 8, "right": 16, "top": 36, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores(),
        yAxis=g.eje_categorias(lista, inverse=True),
        series=[{"name": nombre, "type": "bar", "stack": "i", "barMaxWidth": 26,
                 "data": [sum(1 for i in decl if i["idioma"] == idi and i["nivel"] == nivel) for idi in lista],
                 "itemStyle": {"color": colores[nivel - 1]}}
                for nivel, nombre in cv.NIVELES_IDIOMA.items()],
    )
    ingles_bueno = {i["web_user_id"] for i in decl if i["idioma"] == "Inglés" and i["nivel"] >= 2}
    por_tramo = [_pct(sum(1 for f in filas if f["id"] in ingles_bueno and _tramo(f["edad"]) == t),
                      sum(1 for f in filas if _tramo(f["edad"]) == t)) for t in TRAMOS_ETIQ]
    grafico_tramo = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        xAxis=g.eje_categorias(TRAMOS_ETIQ, name="Edad", nameLocation="middle", nameGap=28),
        yAxis=g.eje_valores("fmt:pct"),
        grid={"left": 8, "right": 16, "top": 24, "bottom": 28, "containLabel": True},
        series=[g.barras("Inglés intermedio o más", por_tramo, g.SERIES[0],
                         label={"show": True, "position": "top", "formatter": "{c}%", "color": g.TINTA_SUAVE})],
    )
    con_idioma = len({i["web_user_id"] for i in decl})
    avanzado = len({i["web_user_id"] for i in decl if i["idioma"] == "Inglés" and i["nivel"] >= 3})
    portugues = len({i["web_user_id"] for i in decl if i["idioma"] == "Portugués"})

    return {
        "kpis": [
            {"label": "Declaran algún idioma", "valor": f"{_pct(con_idioma, total)}%", "detalle": f"{formato_numero(con_idioma)} personas"},
            {"label": "Inglés intermedio o más", "valor": formato_numero(len(ingles_bueno)), "detalle": f"{_pct(len(ingles_bueno), total)}% del total"},
            {"label": "Inglés avanzado o nativo", "valor": formato_numero(avanzado), "detalle": "aptos para puestos bilingües"},
            {"label": "Portugués", "valor": formato_numero(portugues), "detalle": "útil en zonas de frontera y turismo"},
        ],
        "conclusiones": [
            f"{_pct(con_idioma, total)}% declara al menos un idioma; inglés es por lejos el más común.",
            f"Solo {formato_numero(avanzado)} personas tienen inglés avanzado o nativo: la reserva para call center bilingüe es chica.",
            (f"Los más jóvenes tienen mejor inglés: {por_tramo[0]}% en 18–24 contra {por_tramo[-1]}% en 50+."
             if por_tramo[0] > por_tramo[-1] + 3 else
             f"El inglés no cambia mucho con la edad: {por_tramo[0]}% en 18–24 y {por_tramo[-1]}% en 50+."),
            f"{formato_numero(portugues)} declaran portugués, útil para Rivera, Artigas y la temporada en Maldonado.",
        ],
        "secciones": [
            seccion("Idiomas y nivel", grafico=grafico_idiomas, alto=280, detalle="idioma",
                    ayuda_detalle="Hacé clic en una barra para ver quiénes tienen ese idioma con ese nivel.",
                    explicacion="Cantidad de personas que declararon cada idioma, partida por nivel: del celeste (básico) al "
                                "azul oscuro (avanzado) y naranja (nativo o bilingüe).",
                    lectura=[f"Inglés: {formato_numero(sum(1 for i in decl if i['idioma'] == 'Inglés'))} personas."]),
            seccion("Inglés según la edad", grafico=grafico_tramo, alto=280, detalle="ingles_tramo",
                    ayuda_detalle="Hacé clic en un tramo para ver quiénes tienen inglés intermedio o más.",
                    explicacion="Porcentaje de cada tramo de edad que declara inglés de nivel intermedio o superior.",
                    lectura=[f"El tramo con más inglés es {TRAMOS_ETIQ[por_tramo.index(max(por_tramo))]} años ({max(por_tramo)}%)."],
                    acciones=[{"prioridad": "media", "titulo": "Validar el nivel de inglés en la entrevista",
                               "detalle": "El nivel es autodeclarado. Para puestos bilingües, una prueba corta evita "
                                          "presentar candidatos que no cumplen."}]),
        ],
        "sugerencias": ["¿Cuántos candidatos bilingües tenemos?", "¿Dónde buscar gente con portugués?"],
        "contexto_ia": {"con_idioma": con_idioma, "ingles_intermedio_o_mas": len(ingles_bueno),
                        "ingles_avanzado": avanzado, "portugues": portugues},
    }


def _filtro_cv(clave, valor, serie):
    """Filtros de los gráficos del CV: (título, función, columna extra con su valor)."""
    perfil = cv.perfil_cv()
    if clave == "anios_exp":
        return (f"Experiencia: {valor.lower()}", lambda f: _bucket_exp(perfil[f["id"]]["anios_exp"]) == valor,
                ("Años de experiencia", lambda f: str(perfil[f["id"]]["anios_exp"]).replace(".", ",")))
    if clave == "cargo":
        ids = {e["web_user_id"] for e in cv.experiencia() if e["cargo"] == valor}
        meses = {}
        for e in cv.experiencia():
            if e["cargo"] == valor:
                meses[e["web_user_id"]] = max(meses.get(e["web_user_id"], 0), e["meses"])
        return (f"Trabajaron como {valor.lower()}", lambda f: f["id"] in ids,
                ("Meses en el cargo", lambda f: meses.get(f["id"], "")))
    if clave == "permanencia":
        trab = {}
        for e in cv.experiencia():
            if e["actual"] != cv.TRABAJO_ACTUAL_SI and _bucket_perm(e["meses"]) == valor:
                trab.setdefault(e["web_user_id"], f"{e['cargo']} en {e['empresa']} ({e['meses']} m)")
        return (f"Trabajos de {valor.lower()}", lambda f: f["id"] in trab, ("Trabajo", lambda f: trab.get(f["id"], "")))
    if clave == "causal":
        trab = {}
        for e in cv.experiencia():
            if e["causal"] == valor:
                trab.setdefault(e["web_user_id"], f"{e['cargo']} en {e['empresa']}")
        return (f"Salieron por: {valor.lower()}", lambda f: f["id"] in trab, ("Trabajo", lambda f: trab.get(f["id"], "")))
    if clave == "nivel":
        completo = {"Completo": True, "Incompleto": False}.get(serie)
        return ((f"{valor} {serie.lower()}" if completo is not None else f"Nivel máximo: {valor}"),
                lambda f: perfil[f["id"]]["nivel_max"] == valor and (completo is None or perfil[f["id"]]["nivel_completo"] == completo),
                ("Formación", lambda f: f"{perfil[f['id']]['curso']} ({'completo' if perfil[f['id']]['nivel_completo'] else 'incompleto'})"))
    if clave == "curso":
        ids = {fm["web_user_id"] for fm in cv.formacion() if fm["curso"] == valor}
        return (f"Formación: {valor}", lambda f: f["id"] in ids,
                ("Nivel máximo", lambda f: perfil[f["id"]]["nivel_max"] or ""))
    if clave == "idioma":
        nivel = next((n for n, nombre in cv.NIVELES_IDIOMA.items() if nombre == serie), None)
        ids = {i["web_user_id"] for i in cv.idiomas() if i["idioma"] == valor and (nivel is None or i["nivel"] == nivel)}
        return (f"{valor}{' · ' + serie.lower() if nivel else ''}", lambda f: f["id"] in ids,
                ("Idiomas", lambda f: ", ".join(perfil[f["id"]]["idiomas"])))
    if clave == "ingles_tramo":
        ids = {i["web_user_id"] for i in cv.idiomas() if i["idioma"] == "Inglés" and i["nivel"] >= 2}
        return (f"Inglés intermedio o más, {valor} años", lambda f: f["id"] in ids and _tramo(f["edad"]) == valor,
                ("Idiomas", lambda f: ", ".join(perfil[f["id"]]["idiomas"])))
    return None


# ==========================================================================
# Detalle de registros (modal)
# ==========================================================================
def _filtro(clave, valor, serie):
    """Devuelve (título, función que dice si una fila corresponde) según lo cliqueado."""
    if clave == "mes":
        return f"Actualizados en {valor}", lambda f: etiqueta_mes(f["fecha_act"].year, f["fecha_act"].month) == valor
    if clave == "antiguedad":
        return f"Última actualización: {valor.lower()}", lambda f: _antiguedad(f["dias_act"]) == valor
    if clave == "tramo":
        sexo = "F" if serie == "Mujeres" else "M" if serie == "Hombres" else None
        return (f"{serie} de {valor} años" if sexo else f"Registrados de {valor} años",
                lambda f: _tramo(f["edad"]) == valor and (sexo is None or f["sexo"] == sexo))
    if clave == "estado_civil":
        return f"Estado civil: {valor}", lambda f: f["estado_civil"] == valor
    if clave == "departamento":
        return f"Registrados en {valor}", lambda f: _depto(f) == valor
    if clave == "localidad":
        return f"Registrados en {valor}", lambda f: f"{f['localidad']} ({f['departamento']})" == valor
    if clave == "rango_salario":
        return f"Aspiran {valor}", lambda f: f["moneda"] == "UYU" and f["salario_aspirado"] > 0 and _rango(f["salario_aspirado"]) == valor
    if clave == "tramo_salario":
        return f"Con empleo, de {valor} años", lambda f: f["salario_actual"] > 0 and _tramo(f["edad"]) == valor
    if clave == "atributo":
        campo = ATRIBUTOS.get(valor)
        return f"{valor}: sí", lambda f: campo is not None and f[campo] == SI
    if clave == "requisitos":
        n = int(valor.split()[0]) if valor[:1].isdigit() else -1
        return f"Cumplen {valor} requisitos", lambda f: _requisitos(f) == n
    if clave == "faltante":
        fn = CAMPOS.get(valor)
        return f"Sin {valor.lower()}", lambda f: fn is not None and not fn(f)
    if clave == "etapa":
        i = ETAPAS.index(valor) if valor in ETAPAS else 99
        return f"Llegaron a «{valor}»", lambda f: f["etapa"] >= i
    if clave == "grupo":
        grupos = {"Perfil completo": lambda f: f["cv"] and f["salario_aspirado"] > 0 and f["departamento"],
                  "Sin CV": lambda f: not f["cv"], "Sin departamento": lambda f: not f["departamento"],
                  "Actualizado en el último año": lambda f: f["dias_act"] <= 365,
                  "Sin actualizar hace más de 1 año": lambda f: f["dias_act"] > 365}
        fn = grupos.get(valor, lambda f: False)
        return valor, fn
    if clave == "sin_gestion":
        return f"Sin gestionar en {valor}", lambda f: _sin_gestion(f) and _depto(f) == valor
    return "Registros", lambda f: False


# Colores de la columna Etapa en el modal
PILDORAS_ETAPA = {"Solo registro web": "gris", "Pasó a candidato": "violeta", "Entrevistado": "azul", "Ingresado": "verde"}


def detalle(clave, valor, serie, periodo):
    extra = None
    filtro_cv = _filtro_cv(clave, valor, serie)
    if filtro_cv:
        titulo, coincide, extra = filtro_cv
    else:
        titulo, coincide = _filtro(clave, valor, serie)
    # Los análisis de foto actual usan toda la base; los demás, el período elegido
    filas = services.registros(periodo)
    elegidas = sorted((f for f in filas if coincide(f)), key=lambda f: f["dias_act"])

    columnas = list(services.COLUMNAS_DETALLE)
    if extra:
        columnas.insert(6, extra[0])
    salida = []
    for f in elegidas:
        fila = services.fila_detalle(f)
        if extra:
            fila.insert(6, extra[1](f))
        salida.append(fila)

    por_etapa = Counter(ETAPAS[f["etapa"]] for f in elegidas)
    return {
        "titulo": titulo,
        "descripcion": "ordenados por última actualización",
        "columnas": columnas,
        "filas": salida,
        "pildoras": {"Etapa": PILDORAS_ETAPA},
        "resumen": [{"texto": e, "valor": por_etapa.get(e, 0), "color": PILDORAS_ETAPA[e]} for e in ETAPAS],
    }


for _a in catalogo:
    catalogo.detalle(_a["slug"])(detalle)
