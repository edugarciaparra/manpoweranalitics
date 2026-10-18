"""Análisis del módulo Candidatos."""
from collections import Counter, defaultdict

from apps.core import graficos as g
from apps.core.analisis import Catalogo, seccion
from apps.core.estadistica import mediana, pronostico
from apps.core.utils import contar_por_mes, etiqueta_mes, meses_completos, siguientes_meses

from . import services

catalogo = Catalogo()

TRAMOS = [(18, 24), (25, 29), (30, 34), (35, 39), (40, 44), (45, 49), (50, 62)]
BANDAS = [(0, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 10.1)]


def _pct(a, b):
    return round(a / b * 100) if b else 0


def _banda(puntaje):
    for i, (a, b) in enumerate(BANDAS):
        if a <= puntaje < b:
            return i
    return len(BANDAS) - 1


# ==========================================================================
# Perfil y fuentes de candidatos
# ==========================================================================
@catalogo.registrar(
    "perfil", "Perfil y fuentes de candidatos",
    "Quiénes se postulan, de qué canales vienen, cuáles funcionan mejor y cuántos candidatos se esperan.",
    icono="bi-people",
)
def perfil(periodo):
    cand = services.candidatos(periodo)
    total = len(cand)

    # --- Quiénes son ------------------------------------------------------
    etiquetas = [f"{a}–{b}" if b < 62 else f"{a}+" for a, b in TRAMOS]
    def contar(sexo):
        return [sum(1 for c in cand if c["sexo"] == sexo and a <= c["edad"] <= b) for a, b in TRAMOS]
    mujeres, hombres = contar("F"), contar("M")
    grafico_piramide = g.base(
        legend=g.leyenda(data=["Mujeres", "Hombres"]),
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        xAxis=g.eje_valores(axisLabel={"formatter": "fmt:abs", "color": g.TINTA_SUAVE}),
        yAxis=g.eje_categorias(etiquetas, name="Edad", nameLocation="end"),
        series=[
            {"name": "Mujeres", "type": "bar", "stack": "p", "barMaxWidth": 26, "data": [-v for v in mujeres],
             "itemStyle": {"color": g.SERIES[1], "borderRadius": [4, 0, 0, 4]}, "tooltip": {"valueFormatter": "fmt:abs"}},
            {"name": "Hombres", "type": "bar", "stack": "p", "barMaxWidth": 26, "data": hombres,
             "itemStyle": {"color": g.SERIES[0], "borderRadius": [0, 4, 4, 0]}},
        ],
    )
    tramo_top = max(range(len(TRAMOS)), key=lambda i: mujeres[i] + hombres[i])
    niveles = Counter(c["nivel"] for c in cand).most_common()
    deptos = Counter(c["departamento"] for c in cand).most_common()

    # --- De dónde vienen y cuáles funcionan -------------------------------
    por_canal = defaultdict(lambda: [0, 0])
    for c in cand:
        por_canal[c["canal"]][0] += 1
        por_canal[c["canal"]][1] += c["etapa"] == 2
    canales = sorted(por_canal.items(), key=lambda x: -_pct(x[1][1], x[1][0]))
    conv_media = _pct(sum(c["etapa"] == 2 for c in cand), total)
    grafico_canales = g.base(
        legend=g.leyenda(),
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        grid={"left": 8, "right": 16, "top": 36, "bottom": 8, "containLabel": True},
        xAxis=g.eje_categorias([c for c, _ in canales]),
        yAxis=g.eje_valores(),
        series=[
            g.barras("Candidatos", [v[0] for _, v in canales], g.AZUL[1]),
            g.barras("Ingresaron", [v[1] for _, v in canales], g.SERIES[0], barGap="-100%",
                     label={"show": True, "position": "top", "color": g.TINTA_SUAVE, "formatter": "{c}"}),
        ],
    )
    mejor, peor = canales[0], canales[-1]
    mas_volumen = max(canales, key=lambda x: x[1][0])

    # --- Cuántos van a llegar ---------------------------------------------
    meses = meses_completos(24)
    todos = services.candidatos()
    serie = contar_por_mes(todos, meses)
    p = pronostico(serie, pasos=3)
    futuros = siguientes_meses(meses[-1], 3)
    grafico_pronostico = g.serie_pronostico(serie[-12:], p, [etiqueta_mes(*m) for m in meses[-12:]],
                                            [etiqueta_mes(*m) for m in futuros], nombre="Candidatos")
    ingresos_esperados = round(sum(p["valores"]) * conv_media / 100)

    # --- Qué hacer --------------------------------------------------------
    acciones = [
        {"prioridad": "alta", "titulo": f"Potenciar {mejor[0]}",
         "detalle": f"Convierte {_pct(mejor[1][1], mejor[1][0])}% (media {conv_media}%) pero aporta solo "
                    f"{_pct(mejor[1][0], total)}% de los candidatos. Darle más presupuesto o difusión."},
        {"prioridad": "media", "titulo": f"Revisar los avisos en {peor[0]}",
         "detalle": f"Convierte {_pct(peor[1][1], peor[1][0])}%. Ajustar requisitos y textos de los avisos para filtrar mejor."},
    ]
    if deptos and _pct(deptos[0][1], total) > 50:
        acciones.append({"prioridad": "baja", "titulo": "Atraer más candidatos del interior",
                         "detalle": f"{deptos[0][0]} concentra {_pct(deptos[0][1], total)}%. Publicar en medios locales "
                                    "para los pedidos fuera de la capital."})

    return {
        "kpis": [
            {"label": "Candidatos", "valor": total, "detalle": "en el período"},
            {"label": "Edad mediana", "valor": round(mediana([c["edad"] for c in cand])), "detalle": "años"},
            {"label": "Mejor canal", "valor": mejor[0], "detalle": f"{_pct(mejor[1][1], mejor[1][0])}% llega a ingresar"},
            {"label": f"Esperados en {etiqueta_mes(*futuros[0])}", "valor": round(p["valores"][0]),
             "detalle": f"entre {round(p['inferior'][0])} y {round(p['superior'][0])}"},
        ],
        "conclusiones": [
            f"El tramo de edad más frecuente es {etiquetas[tramo_top]} años; {_pct(sum(mujeres), total)}% son mujeres y "
            f"{niveles[0][0].lower()} es el nivel más común.",
            f"{mas_volumen[0]} trae más candidatos, pero {mejor[0]} es el que mejor convierte "
            f"({_pct(mejor[1][1], mejor[1][0])}% contra {conv_media}% de media).",
            f"En los próximos 3 meses llegarían unos {round(sum(p['valores']))} candidatos y {ingresos_esperados} ingresos.",
            f"Mover parte de la difusión a {mejor[0]} mejoraría la calidad de los candidatos sin aumentar el volumen.",
        ],
        "secciones": [
            seccion("Quiénes se postulan", grafico=grafico_piramide, lectura=[
                f"El tramo con más candidatos es {etiquetas[tramo_top]} años.",
                f"{deptos[0][0]} concentra el {_pct(deptos[0][1], total)}% de los candidatos." if deptos else "",
                "Mujeres a la izquierda y hombres a la derecha, por tramo de edad.",
            ], tabla={
                "titulo": "Nivel educativo",
                "columnas": ["Nivel", "Candidatos", "%", "Ingresaron"],
                "filas": [[n, v, f"{_pct(v, total)}%", f"{_pct(sum(1 for c in cand if c['nivel'] == n and c['etapa'] == 2), v)}%"]
                          for n, v in niveles],
            }),
            seccion("De dónde vienen y cuáles funcionan", grafico=grafico_canales, alto=300,
                    descripcion="Candidatos por canal de publicación y cuántos llegaron a ingresar.", lectura=[
                        f"{mas_volumen[0]} aporta {_pct(mas_volumen[1][0], total)}% de los candidatos.",
                        f"{mejor[0]} convierte {_pct(mejor[1][1], mejor[1][0])}% y {peor[0]} solo {_pct(peor[1][1], peor[1][0])}%.",
                    ]),
            seccion("Cuántos candidatos se esperan", grafico=grafico_pronostico, acciones=acciones, lectura=[
                f"Para {etiqueta_mes(*futuros[0])} se esperan unos {round(p['valores'][0])} candidatos.",
                f"Con la conversión actual ({conv_media}%) eso daría unos {ingresos_esperados} ingresos en 3 meses.",
            ]),
        ],
        "sugerencias": ["¿Por qué los referidos convierten más?", "¿En qué canal conviene invertir?",
                        "¿Cómo atraer más candidatos del interior?"],
        "contexto_ia": {"total": total, "por_canal": {c: v for c, v in canales}, "niveles": dict(niveles),
                        "departamentos": dict(deptos), "proyeccion": round(sum(p["valores"]))},
    }


# ==========================================================================
# Probabilidad de ingreso
# ==========================================================================
@catalogo.registrar(
    "probabilidad", "Probabilidad de ingreso",
    "Qué perfil termina ingresando, qué tan probable es para cada candidato en proceso y a quién presentar primero.",
    usa_periodo=False, icono="bi-bullseye",
)
def probabilidad(periodo):
    historia = services.candidatos()
    cerrados = [c for c in historia if not c["en_proceso"]]

    # --- Qué perfil ingresa -----------------------------------------------
    tasa_nivel = []
    for n in services.NIVELES:
        grupo = [c for c in cerrados if c["nivel"] == n]
        tasa_nivel.append(_pct(sum(c["etapa"] == 2 for c in grupo), len(grupo)))
    grafico_nivel = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        grid={"left": 8, "right": 48, "top": 8, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores("fmt:pct", max=100),
        yAxis=g.eje_categorias(services.NIVELES),
        series=[g.barras("Ingresan", tasa_nivel, g.SERIES[0], barMaxWidth=22,
                         itemStyle={"color": g.SERIES[0], "borderRadius": [0, 4, 4, 0]},
                         label={"show": True, "position": "right", "formatter": "{c}%", "color": g.TINTA_SUAVE})],
    )

    # --- Probabilidad según puntaje ---------------------------------------
    tasa = []
    for i in range(len(BANDAS)):
        grupo = [c for c in cerrados if _banda(c["puntaje"]) == i]
        tasa.append(_pct(sum(c["etapa"] == 2 for c in grupo), len(grupo)))
    etiquetas = [f"{a:g}–{b:g}" if b < 10 else f"{a:g}+" for a, b in BANDAS]
    grafico_puntaje = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        grid={"left": 8, "right": 16, "top": 24, "bottom": 36, "containLabel": True},
        xAxis=g.eje_categorias(etiquetas, name="Puntaje (formación 40% + experiencia 60%)", nameLocation="middle", nameGap=30),
        yAxis=g.eje_valores("fmt:pct", max=100),
        series=[g.barras("Probabilidad de ingreso",
                         [{"value": t, "itemStyle": {"color": g.AZUL[min(i + 1, len(g.AZUL) - 1)]}} for i, t in enumerate(tasa)],
                         label={"show": True, "position": "top", "formatter": "{c}%", "color": g.TINTA})],
    )

    # --- A quién presentar primero ----------------------------------------
    en_proceso = sorted([c for c in historia if c["en_proceso"]], key=lambda c: -c["puntaje"])
    prob = {c["id"]: tasa[_banda(c["puntaje"])] for c in en_proceso}
    esperados = sum(prob.values()) / 100
    # Alta / baja probabilidad, relativas a la tasa de ingreso histórica
    media = _pct(sum(c["etapa"] == 2 for c in cerrados), len(cerrados))
    umbral_alto, umbral_bajo = round(media * 1.2), round(media * .6)
    altos = [c for c in en_proceso if prob[c["id"]] >= umbral_alto]
    bajos = [c for c in en_proceso if prob[c["id"]] < umbral_bajo]
    acciones = []
    if altos:
        acciones.append({"prioridad": "alta", "titulo": f"Presentar primero a {len(altos)} candidatos de alta probabilidad",
                         "detalle": f"Tienen {umbral_alto}% o más de chances de ingresar (la media es {media}%). "
                                    "Presentarlos al cliente esta semana: "
                                    + ", ".join(f"#{c['id']} ({c['puesto']})" for c in altos[:4]) + "."})
    puestos_bajos = Counter(c["puesto"] for c in bajos).most_common(1)
    if bajos:
        acciones.append({"prioridad": "media", "titulo": f"Buscar más candidatos para {puestos_bajos[0][0].lower()}",
                         "detalle": f"Hay {len(bajos)} candidatos en proceso con menos de {umbral_bajo}% de probabilidad, sobre todo "
                                    "para ese puesto. Ampliar la búsqueda antes de que venza el pedido."})
    acciones.append({"prioridad": "baja", "titulo": "Usar el puntaje como filtro inicial",
                     "detalle": f"Debajo de 3 puntos la probabilidad es {tasa[0]}%. Revisar esos casos antes de "
                                "dedicarles una entrevista completa."})

    return {
        "kpis": [
            {"label": "En proceso", "valor": len(en_proceso), "detalle": "candidatos sin resultado"},
            {"label": "Ingresos esperados", "valor": round(esperados), "detalle": "suma de probabilidades"},
            {"label": "Alta probabilidad", "valor": len(altos), "detalle": f"{umbral_alto}% o más (media {media}%)"},
            {"label": "Entre extremos de puntaje", "valor": f"{tasa[-1] - tasa[0]} pts",
             "detalle": f"de {tasa[0]}% a {tasa[-1]}%"},
        ],
        "conclusiones": [
            f"El puntaje de la entrevista predice bien el resultado: con {etiquetas[-1]} puntos ingresa el {tasa[-1]}% "
            f"y con menos de 3, el {tasa[0]}%.",
            f"El nivel educativo con más ingresos es {services.NIVELES[tasa_nivel.index(max(tasa_nivel))].lower()} "
            f"({max(tasa_nivel)}%).",
            f"De los {len(en_proceso)} candidatos en proceso se esperan unos {round(esperados)} ingresos.",
            f"Presentar primero a los {len(altos)} de alta probabilidad acorta el tiempo de cierre de los pedidos."
            if altos else "Ningún candidato en proceso supera la media con holgura: conviene ampliar la búsqueda.",
        ],
        "secciones": [
            seccion("Qué perfil termina ingresando", grafico=grafico_nivel, alto=260,
                    descripcion="Porcentaje de candidatos que ingresaron, por nivel educativo.", lectura=[
                        "A mayor nivel educativo, mayor probabilidad de ingresar, aunque la experiencia pesa más.",
                    ]),
            seccion("Probabilidad según el puntaje de la entrevista", grafico=grafico_puntaje, lectura=[
                f"Un candidato con {etiquetas[-1]} puntos tiene {tasa[-1]}% de probabilidad de ingresar.",
                "Se calcula con todos los procesos terminados; los que siguen en curso no se cuentan.",
            ]),
            seccion("A quién presentar primero", acciones=acciones, lectura=[
                "Candidatos en proceso ordenados por puntaje, con su probabilidad de ingresar.",
            ], tabla={
                "titulo": "Candidatos en proceso",
                "columnas": ["Candidato", "Puesto", "Puntaje", "Probabilidad", "Canal"],
                "filas": [[f"#{c['id']}", c["puesto"], c["puntaje"], f"{prob[c['id']]}%", c["canal"]]
                          for c in en_proceso[:10]],
                "vacio": "No hay candidatos en proceso.",
            }),
        ],
        "sugerencias": ["¿Qué pesa más, la formación o la experiencia?",
                        "¿Conviene presentar candidatos con puntaje bajo?", "¿Qué candidato presento primero?"],
        "contexto_ia": {"probabilidad_por_puntaje": dict(zip(etiquetas, tasa)),
                        "por_nivel": dict(zip(services.NIVELES, tasa_nivel)), "en_proceso": len(en_proceso)},
    }
