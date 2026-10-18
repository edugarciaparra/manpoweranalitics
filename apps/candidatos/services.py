"""
Datos del módulo Candidatos y entrevistas.

Por ahora se generan entrevistas de ejemplo con una semilla fija (siempre dan
lo mismo). Al conectar sgo_new, entrevistas() pasa a ser la consulta a
[Entrevistas] + [Candidatos] + [Psicologos], sin datos que identifiquen
a las personas (nombre, documento, teléfono, email, dirección).
"""
import random
from functools import lru_cache

from apps.core.utils import desde_periodo, hace

ETAPAS = ["Entrevistado", "Presentado al cliente", "Ingresado"]
PSICOLOGOS = ["L. Silva", "M. Díaz", "C. Ferreira", "A. Pereira", "S. Olivera"]
CANALES = ["Web Manpower", "LinkedIn", "Computrabajo", "Referido", "Redes sociales"]
DEPARTAMENTOS = ["Montevideo", "Canelones", "San José", "Maldonado", "Colonia"]
NIVELES = ["Primaria", "Secundaria incompleta", "Secundaria completa", "Terciaria", "Universitaria"]
PUESTOS = ["Cajero", "Repositor", "Call center", "Operario de planta", "Administrativo", "Chofer"]


@lru_cache(maxsize=1)
def _generar():
    r = random.Random(20261018)
    # Cada psicólogo tiene su carga y su efectividad, para que el análisis tenga algo que encontrar
    perfil_psico = {"L. Silva": (1.4, 1.15), "M. Díaz": (1.2, .95), "C. Ferreira": (.7, 1.25),
                    "A. Pereira": (1.0, .80), "S. Olivera": (.6, 1.05)}
    efect_canal = {"Web Manpower": 1.0, "LinkedIn": 1.1, "Computrabajo": .85, "Referido": 1.45, "Redes sociales": .75}
    pesos_psico = [perfil_psico[p][0] for p in PSICOLOGOS]

    filas = []
    for i in range(420):
        psico = r.choices(PSICOLOGOS, weights=pesos_psico)[0]
        canal = r.choices(CANALES, weights=[30, 18, 26, 10, 16])[0]
        nivel = r.choices(range(5), weights=[6, 22, 38, 20, 14])[0]
        edad = max(18, min(62, int(r.gauss(31, 9))))
        formacion = round(min(10, max(0, r.gauss(3 + nivel * 1.3, 1.5))), 1)
        experiencia = round(min(10, max(0, r.gauss(2 + (edad - 18) / 6, 2))), 1)
        puntaje = formacion * .4 + experiencia * .6
        prob_presentado = min(.95, .18 + puntaje * .07) * perfil_psico[psico][1] * efect_canal[canal]
        etapa = 0
        if r.random() < prob_presentado:
            etapa = 1
            if r.random() < min(.9, .25 + puntaje * .05):
                etapa = 2
        filas.append({
            "id": i + 1,
            "fecha": hace(int(r.random() ** 1.15 * 365)),
            "psicologo": psico, "canal": canal, "nivel": NIVELES[nivel],
            "departamento": r.choices(DEPARTAMENTOS, weights=[58, 22, 8, 7, 5])[0],
            "sexo": r.choices(["F", "M"], weights=[54, 46])[0],
            "edad": edad, "puesto": r.choice(PUESTOS),
            "formacion": formacion, "experiencia": experiencia, "puntaje": round(puntaje, 1),
            "etapa": etapa, "en_proceso": r.random() < .08 and etapa < 2,
        })
    return filas


def entrevistas(periodo=None):
    filas = _generar()
    if periodo is None:
        return list(filas)
    desde = desde_periodo(periodo)
    return [f for f in filas if f["fecha"] >= desde]


def resumen_landing():
    mes = entrevistas("30")
    return [
        {"valor": len(mes), "texto": "entrevistas en 30 días"},
        {"valor": sum(1 for e in mes if e["etapa"] == 2), "texto": "ingresos"},
    ]
