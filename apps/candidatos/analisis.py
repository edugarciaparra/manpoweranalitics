"""Análisis del módulo Candidatos y entrevistas."""
from collections import Counter, defaultdict

from apps.core import graficos as g
from apps.core.analisis import Catalogo
from apps.core.estadistica import mediana

from . import services
from .services import ETAPAS

catalogo = Catalogo()


def _pct(a, b):
    return round(a / b * 100) if b else 0


# --------------------------------------------------------------------------
# Descriptivo
# --------------------------------------------------------------------------
TRAMOS = [(18, 24), (25, 29), (30, 34), (35, 39), (40, 44), (45, 49), (50, 62)]


@catalogo.registrar(
    "descriptivo", "perfil", "Perfil de los entrevistados",
    "Edad, sexo, nivel educativo y departamento de las personas entrevistadas.",
)
def perfil(periodo):
    ent = services.entrevistas(periodo)
    etiquetas = [f"{a}–{b}" if b < 62 else f"{a}+" for a, b in TRAMOS]

    def contar(sexo):
        return [sum(1 for e in ent if e["sexo"] == sexo and a <= e["edad"] <= b) for a, b in TRAMOS]

    mujeres, hombres = contar("F"), contar("M")
    opcion = g.base(
        legend=g.leyenda(data=["Mujeres", "Hombres"]),
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        grid={"left": 8, "right": 16, "top": 36, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores(axisLabel={"formatter": "fmt:abs", "color": g.TINTA_SUAVE}),
        yAxis=g.eje_categorias(etiquetas, name="Edad", nameLocation="end"),
        series=[
            {"name": "Mujeres", "type": "bar", "stack": "p", "barMaxWidth": 26,
             "data": [-v for v in mujeres], "itemStyle": {"color": g.SERIES[1], "borderRadius": [4, 0, 0, 4]},
             "tooltip": {"valueFormatter": "fmt:abs"}},
            {"name": "Hombres", "type": "bar", "stack": "p", "barMaxWidth": 26,
             "data": hombres, "itemStyle": {"color": g.SERIES[0], "borderRadius": [0, 4, 4, 0]}},
        ],
    )

    niveles = Counter(e["nivel"] for e in ent).most_common()
    deptos = Counter(e["departamento"] for e in ent).most_common()
    total = len(ent)
    return {
        "kpis": [
            {"label": "Entrevistas", "valor": total, "detalle": "en el período"},
            {"label": "Edad mediana", "valor": round(mediana([e["edad"] for e in ent])), "detalle": "años"},
            {"label": "Mujeres", "valor": f"{_pct(sum(mujeres), total)}%", "detalle": f"{sum(mujeres)} entrevistadas"},
            {"label": "Nivel más frecuente", "valor": niveles[0][0] if niveles else "–",
             "detalle": f"{_pct(niveles[0][1], total)}% de los casos" if niveles else ""},
        ],
        "grafico": opcion,
        "lectura": [
            f"El tramo con más entrevistados es {etiquetas[max(range(len(TRAMOS)), key=lambda i: mujeres[i] + hombres[i])]} años.",
            f"{deptos[0][0]} concentra el {_pct(deptos[0][1], total)}% de las entrevistas." if deptos else "",
            "Mujeres a la izquierda y hombres a la derecha, por tramo de edad.",
        ],
        "tabla": {
            "titulo": "Nivel educativo y departamento",
            "columnas": ["Nivel educativo", "Entrevistas", "%", "Departamento", "Entrevistas "],
            "filas": [[n[0], n[1], f"{_pct(n[1], total)}%",
                       deptos[i][0] if i < len(deptos) else "", deptos[i][1] if i < len(deptos) else ""]
                      for i, n in enumerate(niveles)],
        },
        "sugerencias": ["¿El perfil cambia según el puesto?", "¿Cómo atraer más candidatos del interior?"],
        "contexto_ia": {"total": total, "mujeres": sum(mujeres), "hombres": sum(hombres),
                        "niveles": dict(niveles), "departamentos": dict(deptos)},
    }


# --------------------------------------------------------------------------
# Diagnóstico
# --------------------------------------------------------------------------
@catalogo.registrar(
    "diagnostico", "embudo", "Dónde se pierden candidatos",
    "Embudo de selección y conversión por canal de publicación.",
)
def embudo(periodo):
    ent = services.entrevistas(periodo)
    conteo = [sum(1 for e in ent if e["etapa"] >= i) for i in range(len(ETAPAS))]
    colores = [g.AZUL[5], g.AZUL[4], g.AZUL[3]]

    opcion = g.base(
        tooltip={"trigger": "item", "confine": True, "formatter": "{b}: {c}"},
        series=[{
            "type": "funnel", "sort": "none", "gap": 4, "left": "10%", "width": "80%", "top": 10, "bottom": 10,
            "minSize": "18%",
            "label": {"show": True, "position": "inside", "formatter": "{b}\n{c}", "color": "#fff", "fontWeight": 600,
                      "lineHeight": 18},
            "itemStyle": {"borderColor": "#fff", "borderWidth": 0, "borderRadius": 6},
            "data": [{"name": n, "value": v, "itemStyle": {"color": c}} for n, v, c in zip(ETAPAS, conteo, colores)],
        }],
    )

    por_canal = defaultdict(lambda: [0, 0, 0])
    for e in ent:
        for i in range(e["etapa"] + 1):
            por_canal[e["canal"]][i] += 1
    canales = sorted(por_canal.items(), key=lambda x: -_pct(x[1][2], x[1][0]))

    caida_1 = conteo[0] - conteo[1]
    caida_2 = conteo[1] - conteo[2]
    peor = "entre la entrevista y la presentación al cliente" if caida_1 >= caida_2 else \
           "entre la presentación y el ingreso"
    mejor, peor_canal = canales[0], canales[-1]

    return {
        "kpis": [
            {"label": "Conversión total", "valor": f"{_pct(conteo[2], conteo[0])}%",
             "detalle": f"{conteo[2]} ingresos de {conteo[0]} entrevistas"},
            {"label": "Presentados", "valor": f"{_pct(conteo[1], conteo[0])}%", "detalle": "de los entrevistados"},
            {"label": "Ingresan", "valor": f"{_pct(conteo[2], conteo[1])}%", "detalle": "de los presentados"},
            {"label": "Mejor canal", "valor": mejor[0], "detalle": f"{_pct(mejor[1][2], mejor[1][0])}% llega a ingresar"},
        ],
        "grafico": opcion,
        "grafico_alto": 320,
        "lectura": [
            f"La mayor pérdida está {peor}: se quedan afuera {max(caida_1, caida_2)} candidatos.",
            f"{mejor[0]} convierte {_pct(mejor[1][2], mejor[1][0])}% y {peor_canal[0]} solo "
            f"{_pct(peor_canal[1][2], peor_canal[1][0])}%: el canal pesa en la calidad del candidato.",
        ],
        "tabla": {
            "titulo": "Conversión por canal de publicación",
            "columnas": ["Canal", "Entrevistados", "Presentados", "Ingresados", "Conversión"],
            "filas": [[c, v[0], v[1], v[2], f"{_pct(v[2], v[0])}%"] for c, v in canales],
        },
        "sugerencias": ["¿Por qué los referidos convierten más?", "¿En qué canal conviene invertir?"],
        "contexto_ia": {"embudo": dict(zip(ETAPAS, conteo)), "por_canal": {c: v for c, v in canales}},
    }


# --------------------------------------------------------------------------
# Predictivo
# --------------------------------------------------------------------------
BANDAS = [(0, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 10.1)]


def _banda(puntaje):
    for i, (a, b) in enumerate(BANDAS):
        if a <= puntaje < b:
            return i
    return len(BANDAS) - 1


@catalogo.registrar(
    "predictivo", "probabilidad", "Probabilidad de ingreso",
    "Qué tan probable es que un candidato ingrese según su puntaje de formación y experiencia.",
    usa_periodo=False,
)
def probabilidad(periodo):
    historia = services.entrevistas()  # el modelo aprende de toda la historia
    cerrados = [e for e in historia if not e["en_proceso"]]
    tasa = []
    for i in range(len(BANDAS)):
        grupo = [e for e in cerrados if _banda(e["puntaje"]) == i]
        tasa.append(_pct(sum(1 for e in grupo if e["etapa"] == 2), len(grupo)))

    etiquetas = [f"{a:g}–{b:g}" if b < 10 else f"{a:g}+" for a, b in BANDAS]
    opcion = g.base(
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        xAxis=g.eje_categorias(etiquetas, name="Puntaje", nameLocation="middle", nameGap=28),
        yAxis=g.eje_valores("fmt:pct", max=100),
        grid={"left": 8, "right": 16, "top": 24, "bottom": 36, "containLabel": True},
        series=[g.barras("Probabilidad de ingreso",
                         [{"value": t, "itemStyle": {"color": g.AZUL[min(i + 1, len(g.AZUL) - 1)]}} for i, t in enumerate(tasa)],
                         label={"show": True, "position": "top", "formatter": "{c}%", "color": g.TINTA})],
    )

    en_proceso = [e for e in historia if e["en_proceso"]]
    esperados = sum(tasa[_banda(e["puntaje"])] / 100 for e in en_proceso)
    altos = [e for e in en_proceso if tasa[_banda(e["puntaje"])] >= 40]
    return {
        "kpis": [
            {"label": "Candidatos en proceso", "valor": len(en_proceso), "detalle": "todavía sin resultado"},
            {"label": "Ingresos esperados", "valor": round(esperados), "detalle": "suma de probabilidades"},
            {"label": "Con alta probabilidad", "valor": len(altos), "detalle": "40% o más"},
            {"label": "Diferencia entre extremos", "valor": f"{tasa[-1] - tasa[0]} pts",
             "detalle": f"de {tasa[0]}% a {tasa[-1]}%"},
        ],
        "grafico": opcion,
        "lectura": [
            f"Un candidato con puntaje {etiquetas[-1]} tiene {tasa[-1]}% de probabilidad de ingresar; "
            f"con menos de 3 puntos, {tasa[0]}%.",
            "El puntaje combina formación (40%) y experiencia (60%), como en la entrevista.",
            f"De los {len(en_proceso)} candidatos en proceso se esperan unos {round(esperados)} ingresos.",
        ],
        "tabla": {
            "titulo": "Candidatos en proceso con más probabilidad",
            "columnas": ["Entrevista", "Puesto", "Puntaje", "Probabilidad", "Psicólogo"],
            "filas": [[f"#{e['id']}", e["puesto"], e["puntaje"], f"{tasa[_banda(e['puntaje'])]}%", e["psicologo"]]
                      for e in sorted(en_proceso, key=lambda e: -e["puntaje"])[:8]],
        },
        "sugerencias": ["¿Qué pesa más, la formación o la experiencia?", "¿Conviene presentar candidatos con puntaje bajo?"],
        "contexto_ia": {"probabilidad_por_puntaje": dict(zip(etiquetas, tasa)), "en_proceso": len(en_proceso)},
    }


# --------------------------------------------------------------------------
# Prescriptivo
# --------------------------------------------------------------------------
@catalogo.registrar(
    "prescriptivo", "asignacion", "Asignación de entrevistas",
    "Cómo repartir las entrevistas entre psicólogos según su carga y su tasa de ingreso.",
)
def asignacion(periodo):
    ent = services.entrevistas(periodo)
    datos = {}
    for p in services.PSICOLOGOS:
        suyas = [e for e in ent if e["psicologo"] == p]
        datos[p] = {"carga": len(suyas), "conversion": _pct(sum(1 for e in suyas if e["etapa"] == 2), len(suyas))}
    carga_media = sum(d["carga"] for d in datos.values()) / len(datos)
    conv_media = _pct(sum(1 for e in ent if e["etapa"] == 2), len(ent))

    opcion = g.base(
        tooltip={"trigger": "item", "confine": True,
                 "formatter": "{@[2]}<br>Entrevistas: {@[0]}<br>Conversión: {@[1]}%"},
        grid={"left": 36, "right": 90, "top": 32, "bottom": 40, "containLabel": True},
        xAxis=g.eje_valores(name="Entrevistas en el período", nameLocation="middle", nameGap=30, splitLine={"show": False}),
        yAxis=g.eje_valores("fmt:pct", name="Conversión a ingreso", nameLocation="middle", nameGap=44),
        series=[{
            "type": "scatter", "symbolSize": 22,
            "data": [[d["carga"], d["conversion"], p] for p, d in datos.items()],
            "itemStyle": {"color": g.SERIES[0], "borderColor": "#fff", "borderWidth": 2},
            "label": {"show": True, "formatter": "{@[2]}", "position": "right", "color": g.TINTA},
            "labelLayout": {"moveOverlap": "shiftY"},
            "markLine": {"silent": True, "symbol": "none", "lineStyle": {"color": g.EJE, "type": "dashed"},
                         "label": {"color": g.TINTA_SUAVE, "position": "insideEndTop"},
                         "data": [{"xAxis": round(carga_media), "label": {"formatter": "carga media", "position": "end"}},
                                  {"yAxis": conv_media, "label": {"formatter": "conversión media", "position": "insideStartTop"}}]},
        }],
    )

    sobrecargados = [p for p, d in datos.items() if d["carga"] > carga_media * 1.15]
    con_margen = sorted([p for p, d in datos.items() if d["carga"] < carga_media and d["conversion"] >= conv_media],
                        key=lambda p: -datos[p]["conversion"])
    acciones = []
    for p in sorted(sobrecargados, key=lambda p: datos[p]["conversion"]):
        destino = con_margen[0] if con_margen else None
        mover = round(datos[p]["carga"] - carga_media)
        acciones.append({
            "prioridad": "alta" if datos[p]["conversion"] < conv_media else "media",
            "titulo": f"Bajar la carga de {p}",
            "detalle": f"Tiene {datos[p]['carga']} entrevistas ({round(datos[p]['carga'] / carga_media * 100 - 100)}% sobre la media) "
                       f"y convierte {datos[p]['conversion']}%. "
                       + (f"Pasar unas {mover} entrevistas a {destino}, que convierte {datos[destino]['conversion']}%."
                          if destino else "Redistribuir entre el equipo."),
        })
    for p in con_margen:
        if datos[p]["conversion"] > conv_media and not any(p in a["detalle"] for a in acciones):
            acciones.append({
                "prioridad": "media", "titulo": f"Asignar más entrevistas a {p}",
                "detalle": f"Convierte {datos[p]['conversion']}% (media {conv_media}%) con solo {datos[p]['carga']} entrevistas. "
                           "Priorizarle los pedidos más difíciles.",
            })
    bajos = [p for p, d in datos.items() if d["conversion"] < conv_media * .8]
    for p in bajos:
        acciones.append({
            "prioridad": "baja", "titulo": f"Revisar criterios con {p}",
            "detalle": f"Su conversión ({datos[p]['conversion']}%) está bastante debajo de la media. "
                       "Revisar en conjunto algunas entrevistas recientes.",
        })

    mejor = max(datos, key=lambda p: datos[p]["conversion"])
    return {
        "kpis": [
            {"label": "Conversión del equipo", "valor": f"{conv_media}%", "detalle": f"{len(ent)} entrevistas"},
            {"label": "Mejor conversión", "valor": mejor, "detalle": f"{datos[mejor]['conversion']}%"},
            {"label": "Sobrecargados", "valor": len(sobrecargados), "alerta": bool(sobrecargados),
             "detalle": "más de 15% sobre la carga media"},
            {"label": "Carga media", "valor": round(carga_media), "detalle": "entrevistas por psicólogo"},
        ],
        "grafico": opcion,
        "lectura": [
            "Lo ideal es estar arriba a la derecha: mucha carga y buena conversión.",
            f"{mejor} tiene la mejor conversión ({datos[mejor]['conversion']}%)"
            + (f" con poca carga: hay margen para darle más entrevistas." if mejor in con_margen else "."),
            "La conversión depende también del puesto y del canal; conviene mirarla junto con el embudo.",
        ],
        "acciones": acciones,
        "sugerencias": ["¿Cómo reparto las entrevistas de la semana que viene?", "¿Por qué difiere tanto la conversión?"],
        "contexto_ia": {"psicologos": datos, "conversion_media": conv_media},
    }
