"""
Procesos de selección de ejemplo, compartidos por los módulos Candidatos y
Entrevistas mientras no está conectada la base.

Cada fila es un candidato entrevistado para un pedido, con su perfil, el
psicólogo que lo entrevistó y hasta qué etapa llegó. Se generan con una
semilla fija, así que siempre dan lo mismo.

Al conectar sgo_new esto se reemplaza por consultas a [Entrevistas],
[Candidatos] y [Psicologos], sin datos que identifiquen a las personas.
"""
import random
from functools import lru_cache

from apps.core.utils import hace

ETAPAS = ["Entrevistado", "Presentado al cliente", "Ingresado"]
PSICOLOGOS = ["L. Silva", "M. Díaz", "C. Ferreira", "A. Pereira", "S. Olivera"]
CANALES = ["Web Manpower", "LinkedIn", "Computrabajo", "Referido", "Redes sociales"]
DEPARTAMENTOS = ["Montevideo", "Canelones", "San José", "Maldonado", "Colonia"]
NIVELES = ["Primaria", "Secundaria incompleta", "Secundaria completa", "Terciaria", "Universitaria"]
PUESTOS = ["Cajero", "Repositor", "Call center", "Operario de planta", "Administrativo", "Chofer"]

# Qué tan fácil es cubrir cada puesto (multiplica la chance de ingresar)
FACILIDAD_PUESTO = {"Cajero": 1.0, "Repositor": 1.15, "Call center": .85, "Operario de planta": 1.05,
                    "Administrativo": .95, "Chofer": .6}


@lru_cache(maxsize=1)
def procesos():
    r = random.Random(20261018)
    # Cada psicólogo tiene su carga y su efectividad, para que los análisis tengan algo que encontrar
    perfil_psico = {"L. Silva": (1.4, 1.0), "M. Díaz": (1.3, .95), "C. Ferreira": (.75, 1.3),
                    "A. Pereira": (1.0, .75), "S. Olivera": (.6, 1.05)}
    efect_canal = {"Web Manpower": 1.0, "LinkedIn": 1.1, "Computrabajo": .85, "Referido": 1.5, "Redes sociales": .7}
    pesos_psico = [perfil_psico[p][0] for p in PSICOLOGOS]

    filas = []
    for i in range(900):
        # Más volumen reciente: la operación viene creciendo
        dias = int((r.random() ** 1.25) * 730)
        psico = r.choices(PSICOLOGOS, weights=pesos_psico)[0]
        canal = r.choices(CANALES, weights=[30, 18, 26, 10, 16])[0]
        puesto = r.choices(PUESTOS, weights=[24, 22, 18, 14, 12, 10])[0]
        nivel = r.choices(range(5), weights=[6, 22, 38, 20, 14])[0]
        edad = max(18, min(62, int(r.gauss(31, 9))))
        formacion = round(min(10, max(0, r.gauss(3 + nivel * 1.3, 1.5))), 1)
        experiencia = round(min(10, max(0, r.gauss(2 + (edad - 18) / 6, 2))), 1)
        puntaje = formacion * .4 + experiencia * .6

        prob_presentado = min(.95, (.18 + puntaje * .07) * perfil_psico[psico][1] * efect_canal[canal])
        etapa = 0
        if r.random() < prob_presentado:
            etapa = 1
            if r.random() < min(.9, (.25 + puntaje * .05) * FACILIDAD_PUESTO[puesto]):
                etapa = 2
        en_proceso = dias < 20 and etapa < 2 and r.random() < .55

        filas.append({
            "id": i + 1, "fecha": hace(dias), "psicologo": psico, "canal": canal, "puesto": puesto,
            "nivel": NIVELES[nivel], "departamento": r.choices(DEPARTAMENTOS, weights=[58, 22, 8, 7, 5])[0],
            "sexo": r.choices(["F", "M"], weights=[54, 46])[0], "edad": edad,
            "formacion": formacion, "experiencia": experiencia, "puntaje": round(puntaje, 1),
            "etapa": etapa, "en_proceso": en_proceso,
        })
    return tuple(filas)
