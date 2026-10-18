"""Análisis del módulo Entrevistas."""
from collections import defaultdict

from apps.core import graficos as g
from apps.core.analisis import Catalogo, seccion
from apps.core.estadistica import pronostico
from apps.core.utils import contar_por_mes, etiqueta_mes, meses_completos, siguientes_meses

from . import services
from .services import ETAPAS

catalogo = Catalogo()


def _pct(a, b):
    return round(a / b * 100) if b else 0


# ==========================================================================
# Embudo de selección
# ==========================================================================
@catalogo.registrar(
    "embudo", "Embudo de selección",
    "Cómo avanzan los candidatos desde la entrevista hasta el ingreso, en qué puestos se pierden y cuántos ingresos se esperan.",
    icono="bi-funnel",
)
def embudo(periodo):
    ent = services.entrevistas(periodo)
    conteo = [sum(1 for e in ent if e["etapa"] >= i) for i in range(len(ETAPAS))]

    # --- Cómo avanza ------------------------------------------------------
    grafico_embudo = g.base(
        tooltip={"trigger": "item", "confine": True, "formatter": "{b}: {c}"},
        series=[{
            "type": "funnel", "sort": "none", "gap": 4, "left": "10%", "width": "80%", "top": 10, "bottom": 10,
            "minSize": "18%",
            "label": {"show": True, "position": "inside", "formatter": "{b}\n{c}", "color": "#fff",
                      "fontWeight": 600, "lineHeight": 18},
            "itemStyle": {"borderColor": "#fff", "borderWidth": 0, "borderRadius": 6},
            "data": [{"name": n, "value": v, "itemStyle": {"color": c}}
                     for n, v, c in zip(ETAPAS, conteo, [g.AZUL[5], g.AZUL[4], g.AZUL[3]])],
        }],
    )
    caida_1, caida_2 = conteo[0] - conteo[1], conteo[1] - conteo[2]
    etapa_critica = "entre la entrevista y la presentación al cliente" if caida_1 >= caida_2 else \
                    "entre la presentación y el ingreso"

    # --- En qué puestos se pierden ----------------------------------------
    por_puesto = defaultdict(lambda: [0, 0, 0])
    for e in ent:
        por_puesto[e["puesto"]][e["etapa"]] += 1
    puestos = sorted(por_puesto, key=lambda p: _pct(por_puesto[p][2], sum(por_puesto[p])))
    def pct_etapa(p, i):
        return _pct(por_puesto[p][i], sum(por_puesto[p]))
    grafico_puestos = g.base(
        legend=g.leyenda(data=["No presentado", "Presentado, no ingresó", "Ingresó"]),
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}, "valueFormatter": "fmt:pct"},
        grid={"left": 8, "right": 16, "top": 36, "bottom": 8, "containLabel": True},
        xAxis=g.eje_valores("fmt:pct", max=100),
        yAxis=g.eje_categorias(puestos),
        series=[
            {"name": "No presentado", "type": "bar", "stack": "e", "barMaxWidth": 24,
             "data": [pct_etapa(p, 0) for p in puestos], "itemStyle": {"color": g.NEUTRO}},
            {"name": "Presentado, no ingresó", "type": "bar", "stack": "e",
             "data": [pct_etapa(p, 1) for p in puestos], "itemStyle": {"color": g.AZUL[1]}},
            {"name": "Ingresó", "type": "bar", "stack": "e", "data": [pct_etapa(p, 2) for p in puestos],
             "itemStyle": {"color": g.SERIES[0], "borderRadius": [0, 4, 4, 0]},
             "label": {"show": True, "position": "insideRight", "formatter": "{c}%", "color": "#fff", "fontWeight": 600}},
        ],
    )
    peor, mejor = puestos[0], puestos[-1]
    conv = _pct(conteo[2], conteo[0])

    # --- Cuántos ingresos se esperan --------------------------------------
    meses = meses_completos(24)
    todos = services.entrevistas()
    serie = contar_por_mes(todos, meses, filtro=lambda e: e["etapa"] == 2)
    p = pronostico(serie, pasos=3)
    futuros = siguientes_meses(meses[-1], 3)
    grafico_pronostico = g.serie_pronostico(serie[-12:], p, [etiqueta_mes(*m) for m in meses[-12:]],
                                            [etiqueta_mes(*m) for m in futuros], nombre="Ingresos")

    # --- Qué hacer --------------------------------------------------------
    acciones = []
    if pct_etapa(peor, 0) > 50:
        acciones.append({"prioridad": "alta", "titulo": f"Revisar el perfil buscado para {peor.lower()}",
                         "detalle": f"El {pct_etapa(peor, 0)}% de los entrevistados no llega a presentarse. Validar con "
                                    "los clientes los requisitos reales y ajustar los avisos."})
    if caida_2 > caida_1 * .6:
        acciones.append({"prioridad": "media", "titulo": "Preparar mejor a los candidatos antes de presentarlos",
                         "detalle": f"{caida_2} candidatos presentados no ingresaron. Una llamada previa para confirmar "
                                    "disponibilidad y condiciones evita rechazos en la última etapa."})
    acciones.append({"prioridad": "baja", "titulo": f"Replicar lo que funciona en {mejor.lower()}",
                     "detalle": f"Ingresa el {pct_etapa(mejor, 2)}% de los entrevistados. Revisar qué fuentes y "
                                "criterios se usan para ese puesto."})

    return {
        "kpis": [
            {"label": "Entrevistas", "valor": conteo[0], "detalle": "en el período"},
            {"label": "Conversión total", "valor": f"{conv}%", "detalle": f"{conteo[2]} ingresos"},
            {"label": "Puesto más difícil", "valor": peor, "alerta": True,
             "detalle": f"ingresa {pct_etapa(peor, 2)}%"},
            {"label": f"Ingresos esperados en {etiqueta_mes(*futuros[0])}", "valor": round(p["valores"][0]),
             "detalle": f"entre {round(p['inferior'][0])} y {round(p['superior'][0])}"},
        ],
        "conclusiones": [
            f"De cada 100 entrevistados ingresan {conv}.",
            f"La mayor pérdida está {etapa_critica}: se quedan afuera {max(caida_1, caida_2)} candidatos.",
            f"{peor} es el puesto más difícil (ingresa {pct_etapa(peor, 2)}%) y {mejor} el más fácil ({pct_etapa(mejor, 2)}%).",
            f"En los próximos 3 meses se esperan unos {round(sum(p['valores']))} ingresos.",
        ],
        "secciones": [
            seccion("Cómo avanza el proceso", grafico=grafico_embudo, alto=300, lectura=[
                f"{_pct(conteo[1], conteo[0])}% de los entrevistados se presenta al cliente y "
                f"{_pct(conteo[2], conteo[1])}% de los presentados ingresa.",
            ]),
            seccion("En qué puestos se pierden candidatos", grafico=grafico_puestos, alto=320,
                    descripcion="Hasta dónde llegan los entrevistados de cada puesto.", lectura=[
                        f"En {peor.lower()}, {pct_etapa(peor, 0)}% de los entrevistados no llega a presentarse.",
                        "Los puestos están ordenados de menor a mayor conversión.",
                    ]),
            seccion("Cuántos ingresos se esperan", grafico=grafico_pronostico, acciones=acciones, lectura=[
                f"Para {etiqueta_mes(*futuros[0])} se esperan unos {round(p['valores'][0])} ingresos.",
                "La proyección usa los últimos 24 meses completos.",
            ]),
        ],
        "sugerencias": [f"¿Por qué cuesta tanto cubrir {peor.lower()}?", "¿Cómo reducimos la pérdida en la presentación?",
                        "¿Cuántos ingresos vamos a tener este trimestre?"],
        "contexto_ia": {"embudo": dict(zip(ETAPAS, conteo)), "por_puesto": {p: v for p, v in por_puesto.items()}},
    }


# ==========================================================================
# Desempeño de psicólogos
# ==========================================================================
@catalogo.registrar(
    "psicologos", "Desempeño de psicólogos",
    "Carga y efectividad de cada psicólogo, cómo evolucionó y cómo repartir mejor las entrevistas.",
    icono="bi-person-workspace",
)
def psicologos(periodo):
    ent = services.entrevistas(periodo)
    datos = {}
    for ps in services.PSICOLOGOS:
        suyas = [e for e in ent if e["psicologo"] == ps]
        datos[ps] = {"carga": len(suyas), "conversion": _pct(sum(e["etapa"] == 2 for e in suyas), len(suyas))}
    carga_media = sum(d["carga"] for d in datos.values()) / len(datos)
    conv_media = _pct(sum(e["etapa"] == 2 for e in ent), len(ent))

    # --- Carga y efectividad ----------------------------------------------
    grafico_carga = g.base(
        tooltip={"trigger": "item", "confine": True, "formatter": "{@[2]}<br>Entrevistas: {@[0]}<br>Conversión: {@[1]}%"},
        grid={"left": 36, "right": 90, "top": 32, "bottom": 40, "containLabel": True},
        xAxis=g.eje_valores(name="Entrevistas en el período", nameLocation="middle", nameGap=30, splitLine={"show": False}),
        yAxis=g.eje_valores("fmt:pct", name="Conversión a ingreso", nameLocation="middle", nameGap=44),
        series=[{
            "type": "scatter", "symbolSize": 22, "data": [[d["carga"], d["conversion"], ps] for ps, d in datos.items()],
            "itemStyle": {"color": g.SERIES[0], "borderColor": "#fff", "borderWidth": 2},
            "label": {"show": True, "formatter": "{@[2]}", "position": "right", "color": g.TINTA},
            "labelLayout": {"moveOverlap": "shiftY"},
            "markLine": {"silent": True, "symbol": "none", "lineStyle": {"color": g.EJE, "type": "dashed"},
                         "label": {"color": g.TINTA_SUAVE},
                         "data": [{"xAxis": round(carga_media), "label": {"formatter": "carga media", "position": "end"}},
                                  {"yAxis": conv_media, "label": {"formatter": "conversión media", "position": "insideStartTop"}}]},
        }],
    )
    mejor = max(datos, key=lambda ps: datos[ps]["conversion"])

    # --- Evolución por mes ------------------------------------------------
    meses = meses_completos(6)
    todos = services.entrevistas()
    grafico_evolucion = g.base(
        legend=g.leyenda(),
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "shadow"}},
        xAxis=g.eje_categorias([etiqueta_mes(*m) for m in meses]),
        yAxis=g.eje_valores(),
        series=[{"name": ps, "type": "bar", "stack": "m", "barMaxWidth": 40,
                 "data": contar_por_mes(todos, meses, filtro=lambda e, ps=ps: e["psicologo"] == ps),
                 "itemStyle": {"color": g.SERIES[i], "borderColor": "#fff", "borderWidth": 1}}
                for i, ps in enumerate(services.PSICOLOGOS)],
    )
    por_mes_total = contar_por_mes(todos, meses)

    # --- Cómo repartir ----------------------------------------------------
    sobrecargados = [ps for ps, d in datos.items() if d["carga"] > carga_media * 1.15]
    con_margen = sorted([ps for ps, d in datos.items() if d["carga"] < carga_media and d["conversion"] >= conv_media],
                        key=lambda ps: -datos[ps]["conversion"])
    acciones = []
    for ps in sorted(sobrecargados, key=lambda ps: datos[ps]["conversion"]):
        destino = con_margen[0] if con_margen else None
        mover = round(datos[ps]["carga"] - carga_media)
        acciones.append({
            "prioridad": "alta" if datos[ps]["conversion"] < conv_media else "media",
            "titulo": f"Bajar la carga de {ps}",
            "detalle": f"Tiene {datos[ps]['carga']} entrevistas ({round(datos[ps]['carga'] / carga_media * 100 - 100)}% sobre la media) "
                       f"y convierte {datos[ps]['conversion']}%. "
                       + (f"Pasar unas {mover} entrevistas a {destino}, que convierte {datos[destino]['conversion']}%."
                          if destino else "Redistribuir entre el equipo."),
        })
    for ps in con_margen:
        if datos[ps]["conversion"] > conv_media and not any(ps in a["detalle"] for a in acciones):
            acciones.append({"prioridad": "media", "titulo": f"Asignar más entrevistas a {ps}",
                             "detalle": f"Convierte {datos[ps]['conversion']}% (media {conv_media}%) con solo "
                                        f"{datos[ps]['carga']} entrevistas. Priorizarle los pedidos más difíciles."})
    for ps, d in datos.items():
        if d["conversion"] < conv_media * .8:
            acciones.append({"prioridad": "baja", "titulo": f"Revisar criterios con {ps}",
                             "detalle": f"Su conversión ({d['conversion']}%) está bastante debajo de la media. "
                                        "Revisar en conjunto algunas entrevistas recientes."})

    return {
        "kpis": [
            {"label": "Conversión del equipo", "valor": f"{conv_media}%", "detalle": f"{len(ent)} entrevistas"},
            {"label": "Mejor conversión", "valor": mejor, "detalle": f"{datos[mejor]['conversion']}%"},
            {"label": "Sobrecargados", "valor": len(sobrecargados), "alerta": bool(sobrecargados),
             "detalle": "más de 15% sobre la carga media"},
            {"label": "Carga media", "valor": round(carga_media), "detalle": "entrevistas por psicólogo"},
        ],
        "conclusiones": [
            f"{mejor} tiene la mejor conversión ({datos[mejor]['conversion']}%)"
            + (" y le sobra capacidad." if mejor in con_margen else "."),
            (f"{', '.join(sobrecargados)} {'tienen' if len(sobrecargados) > 1 else 'tiene'} más de 15% de carga sobre la media."
             if sobrecargados else "La carga está bien repartida en el equipo."),
            f"El volumen mensual pasó de {por_mes_total[0]} a {por_mes_total[-1]} entrevistas en los últimos 6 meses.",
            "Pasar entrevistas de los más cargados a quienes convierten mejor sube la conversión del equipo sin sumar gente.",
        ],
        "secciones": [
            seccion("Carga y efectividad de cada psicólogo", grafico=grafico_carga, alto=340, lectura=[
                "Lo ideal es estar arriba a la derecha: mucha carga y buena conversión.",
                "La conversión también depende del puesto y del canal: conviene mirarla junto con el embudo.",
            ]),
            seccion("Cómo evolucionó la carga", grafico=grafico_evolucion, descripcion="Entrevistas por mes y psicólogo.", lectura=[
                f"En el último mes completo se hicieron {por_mes_total[-1]} entrevistas.",
            ]),
            seccion("Cómo repartir las entrevistas", acciones=acciones, lectura=[
                "Las recomendaciones buscan equilibrar la carga y darle más volumen a quien mejor convierte.",
            ], tabla={
                "titulo": "Resumen por psicólogo",
                "columnas": ["Psicólogo", "Entrevistas", "Conversión", "Contra la media"],
                "filas": [[ps, d["carga"], f"{d['conversion']}%", f"{d['conversion'] - conv_media:+d} pts"]
                          for ps, d in sorted(datos.items(), key=lambda x: -x[1]["conversion"])],
            }),
        ],
        "sugerencias": ["¿Cómo reparto las entrevistas de la semana que viene?",
                        "¿Por qué difiere tanto la conversión?", "¿Quién debería tomar los pedidos difíciles?"],
        "contexto_ia": {"psicologos": datos, "conversion_media": conv_media},
    }
