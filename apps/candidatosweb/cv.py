"""
Datos del CV de los candidatos web: experiencia, formación e idiomas.

Tablas reales:
    [CVExperiencia]   WebUserId, CVExpId, CVExpEmpresa, CVExpFechaIngreso, CVExpFechaEgreso,
                      CVExpTrabajoActual, CausalBajaId -> [CausalesBaja], CVExpBaja, CVExpTareas, CVExpCargo
    [CVFormacion]     WebUserId, CVFormId, CursoId -> [CursosCarreras] -> [NivelesEducativos],
                      CVFormTitulo, CVFormFechaInicio, CVFormFechaFin, CVFormCompleto, CVFormInstitucion, ...
    [CVIdiomas]       WebUserId, CVIdiomaId -> [Competencias], CVIdiomaNivel, CVIdiomaAniosExp

Por ahora se generan datos de ejemplo con semilla fija, uno o varios registros por
cada candidato web. Al conectar sgo_new cada función pasa a ser su consulta.
"""
import random
from datetime import date, timedelta
from functools import lru_cache

from .services import SI, candidatos_web

# Valores supuestos de los campos de una letra / niveles; ajustar con la consulta de códigos
TRABAJO_ACTUAL_SI = SI
FORMACION_COMPLETA_SI = SI
NIVELES_IDIOMA = {1: "Básico", 2: "Intermedio", 3: "Avanzado", 4: "Nativo / bilingüe"}

NIVELES_EDUCATIVOS = ["Primaria", "Ciclo básico", "Bachillerato", "Técnico / UTU", "Terciario", "Universitario", "Posgrado"]
CURSOS = {
    "Primaria": ["Primaria"],
    "Ciclo básico": ["Ciclo básico"],
    "Bachillerato": ["Bachillerato diversificado", "Bachillerato tecnológico"],
    "Técnico / UTU": ["Administración", "Electricidad", "Gastronomía", "Informática", "Mecánica automotriz", "Logística"],
    "Terciario": ["Analista programador", "Técnico en RRHH", "Marketing", "Operador logístico"],
    "Universitario": ["Contador público", "Lic. en Administración", "Ingeniería en sistemas", "Psicología",
                      "Lic. en Comunicación", "Derecho"],
    "Posgrado": ["Maestría en Administración", "Posgrado en RRHH"],
}
INSTITUCIONES = {
    "Primaria": ["Escuela pública"], "Ciclo básico": ["Liceo público", "Liceo privado"],
    "Bachillerato": ["Liceo público", "Liceo privado"], "Técnico / UTU": ["UTU"],
    "Terciario": ["UTU", "BIOS", "ORT"], "Universitario": ["UdelaR", "ORT", "UCU", "UM"],
    "Posgrado": ["UdelaR", "UCU", "ORT", "UM"],
}
CARGOS = {
    "Cajero/a": 16, "Repositor/a": 14, "Atención al cliente": 12, "Vendedor/a": 11, "Operario/a": 10,
    "Administrativo/a": 9, "Auxiliar de depósito": 7, "Chofer": 4, "Recepcionista": 4, "Mozo/a": 4,
    "Limpieza": 4, "Seguridad": 3, "Analista": 3, "Encargado/a": 3, "Telemarketer": 5,
}
EMPRESAS = ["Supermercado del Este", "Comercial Norte", "Logística Sur", "Call Center Uno", "Industrias Unidas",
            "Farmacia Central", "Distribuidora Oeste", "Restaurante La Plaza", "Servicios Generales", "Hotel Costa",
            "Transporte Rápido", "Tienda Moda", "Estudio Contable", "Constructora Andes"]
CAUSALES = {"Renuncia por mejor oferta": 30, "Fin de contrato / zafra": 26, "Despido": 12, "Cierre de la empresa": 6,
            "Motivos personales": 14, "Estudios": 7, "Mudanza": 5}
IDIOMAS = {"Inglés": 70, "Portugués": 25, "Italiano": 3, "Francés": 3, "Alemán": 1}


def _aleatorio(semilla):
    return random.Random(semilla)


@lru_cache(maxsize=1)
def experiencia():
    """Una fila por trabajo declarado (como [CVExperiencia])."""
    r = _aleatorio(1311)
    hoy = date.today()
    filas = []
    for c in candidatos_web():
        edad_laboral = max(0, c["edad"] - 18)
        # Los que avanzaron en el proceso suelen tener más experiencia
        pesos = [6, 20, 28, 22, 14, 10] if c["etapa"] >= 2 else [16, 27, 26, 17, 9, 5]
        cantidad = min(r.choices([0, 1, 2, 3, 4, 5], weights=pesos)[0], 1 + edad_laboral // 2)
        fin = hoy
        actual_pendiente = c["salario_actual"] > 0
        for i in range(cantidad):
            meses = max(1, int(r.expovariate(1 / 22)))
            es_actual = actual_pendiente and i == 0
            egreso = fin if es_actual else fin - timedelta(days=r.randint(15, 240))
            ingreso = egreso - timedelta(days=meses * 30)
            if ingreso.year < hoy.year - edad_laboral - 1:
                break
            filas.append({
                "web_user_id": c["id"], "id": i + 1, "empresa": r.choice(EMPRESAS),
                "cargo": r.choices(list(CARGOS), weights=list(CARGOS.values()))[0],
                "ingreso": ingreso, "egreso": egreso, "meses": meses,
                "actual": TRABAJO_ACTUAL_SI if es_actual else "N",
                "causal": None if es_actual else r.choices(list(CAUSALES), weights=list(CAUSALES.values()))[0],
            })
            fin = ingreso
    return tuple(filas)


@lru_cache(maxsize=1)
def formacion():
    """Una fila por estudio declarado (como [CVFormacion] + [CursosCarreras])."""
    r = _aleatorio(2718)
    hoy = date.today()
    filas = []
    for c in candidatos_web():
        pesos = [2, 9, 33, 20, 15, 17, 4] if c["etapa"] >= 2 else [5, 15, 34, 16, 12, 15, 3]
        maximo = r.choices(range(len(NIVELES_EDUCATIVOS)), weights=pesos)[0]
        if c["edad"] < 23:
            maximo = min(maximo, 4)
        niveles = sorted({maximo} | ({maximo - 1} if maximo > 1 and r.random() < .35 else set()))
        for i, n in enumerate(niveles):
            nivel = NIVELES_EDUCATIVOS[n]
            completo = r.random() < (.62 if n == maximo else .95)
            inicio = hoy - timedelta(days=r.randint(400, 365 * max(2, c["edad"] - 14)))
            filas.append({
                "web_user_id": c["id"], "id": i + 1, "nivel": nivel, "nivel_orden": n,
                "curso": r.choice(CURSOS[nivel]), "institucion": r.choice(INSTITUCIONES[nivel]),
                "completo": FORMACION_COMPLETA_SI if completo else "N",
                "inicio": inicio, "fin": inicio + timedelta(days=365 * r.randint(1, 5)),
            })
    return tuple(filas)


@lru_cache(maxsize=1)
def idiomas():
    """Una fila por idioma declarado (como [CVIdiomas] + [Competencias])."""
    r = _aleatorio(3141)
    filas = []
    for c in candidatos_web():
        joven = c["edad"] < 30
        cantidad = r.choices([0, 1, 2, 3], weights=[32, 42, 20, 6] if joven else [52, 34, 11, 3])[0]
        elegidos = set()
        while len(elegidos) < cantidad:
            elegidos.add(r.choices(list(IDIOMAS), weights=list(IDIOMAS.values()))[0])
        for idioma in elegidos:
            nivel = r.choices([1, 2, 3, 4], weights=[28, 38, 26, 8] if joven else [48, 34, 14, 4])[0]
            filas.append({"web_user_id": c["id"], "idioma": idioma, "nivel": nivel,
                          "anios": max(0, int(r.gauss(nivel * 2, 2)))})
    return tuple(filas)


# --- Resúmenes por candidato ------------------------------------------------
@lru_cache(maxsize=1)
def perfil_cv():
    """{web_user_id: {anios_exp, trabajos, nivel_max, nivel_completo, idiomas}} para cruzar con los registros."""
    perfil = {c["id"]: {"anios_exp": 0.0, "trabajos": 0, "nivel_max": None, "nivel_orden": -1,
                        "nivel_completo": False, "curso": "", "idiomas": []} for c in candidatos_web()}
    for e in experiencia():
        p = perfil[e["web_user_id"]]
        p["anios_exp"] += e["meses"] / 12
        p["trabajos"] += 1
    for f in formacion():
        p = perfil[f["web_user_id"]]
        if f["nivel_orden"] > p["nivel_orden"]:
            p.update(nivel_max=f["nivel"], nivel_orden=f["nivel_orden"], curso=f["curso"],
                     nivel_completo=f["completo"] == FORMACION_COMPLETA_SI)
    for i in idiomas():
        perfil[i["web_user_id"]]["idiomas"].append(f"{i['idioma']} ({NIVELES_IDIOMA[i['nivel']].split(' ')[0].lower()})")
    for p in perfil.values():
        p["anios_exp"] = round(p["anios_exp"], 1)
    return perfil
