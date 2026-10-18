"""
Datos del módulo Candidatos web (tabla [CandidatosWeb]).

Por ahora se generan registros de ejemplo con las mismas columnas que la tabla
real y una semilla fija (siempre dan lo mismo). Los nombres, documentos,
emails y teléfonos son inventados.

Al conectar sgo_new, candidatos_web() pasa a ser la consulta de abajo
(CONSULTA_SGO) y el resto del módulo queda igual.

Importante: la tabla no tiene fecha de alta. La única fecha es
WebUserFechaAct (última actualización del registro).
"""
import random
from functools import lru_cache

from apps.core.utils import hace

# Valores de los campos de una letra. Ajustar cuando tengamos el resultado
# de la consulta de códigos.
SI = "S"

DEPARTAMENTOS = {
    "Montevideo": 46, "Canelones": 19, "Maldonado": 6, "San José": 4, "Colonia": 4, "Paysandú": 3,
    "Salto": 3, "Rivera": 2, "Soriano": 2, "Florida": 2, "Rocha": 2, "Tacuarembó": 2,
    "Cerro Largo": 1, "Durazno": 1, "Lavalleja": 1, "Artigas": 1, "Río Negro": 1, "Treinta y Tres": 1, "Flores": 1,
}
LOCALIDADES = {
    "Montevideo": ["Centro", "Cordón", "Pocitos", "Malvín", "Unión", "Cerro", "Colón", "Piedras Blancas",
                   "La Teja", "Buceo", "Carrasco", "Paso de la Arena"],
    "Canelones": ["Ciudad de la Costa", "Las Piedras", "Pando", "La Paz", "Canelones", "Progreso", "Santa Lucía"],
    "Maldonado": ["Maldonado", "Punta del Este", "San Carlos", "Piriápolis"],
}
ESTADOS_CIVILES = {"Soltero/a": 58, "Casado/a": 22, "Unión libre": 14, "Divorciado/a": 5, "Viudo/a": 1}
NOMBRES_F = ["María", "Lucía", "Sofía", "Valentina", "Camila", "Florencia", "Agustina", "Micaela", "Natalia",
             "Carolina", "Paula", "Andrea", "Gabriela", "Laura", "Victoria", "Martina", "Romina", "Silvia"]
NOMBRES_M = ["Juan", "Martín", "Diego", "Pablo", "Nicolás", "Santiago", "Federico", "Gonzalo", "Matías",
             "Sebastián", "Bruno", "Rodrigo", "Andrés", "Facundo", "Joaquín", "Emiliano", "Marcelo", "Luis"]
APELLIDOS = ["Rodríguez", "González", "Fernández", "Pérez", "García", "López", "Martínez", "Silva", "Sosa",
             "Díaz", "Pereira", "Suárez", "Romero", "Álvarez", "Ramos", "Acosta", "Benítez", "Núñez",
             "Cabrera", "Olivera", "Castro", "Méndez", "Ferreira", "Machado"]

# Etapa a la que llegó cada registro web dentro de Manpower
ETAPAS = ["Solo registro web", "Pasó a candidato", "Entrevistado", "Ingresado"]

CONSULTA_SGO = """
SELECT cw.[WebUserId], cw.[WebUserNombre], cw.[WebUserApellido], cw.[WebUserNroDocumento],
       cw.[WebUserEmail], cw.[WebUserCelular], cw.[WebUserTelefono], d.[DepartamentoNombre],
       l.[LocalidadNombre], cw.[WebUserSexo], cw.[WebUserFechaNacimiento], cw.[WebUserSalarioActual],
       cw.[WebUserSalarioAspirado], cw.[WebUserSalarioAspiradoMoneda], cw.[WebUserDisponibilidadHoraria],
       cw.[WebUserHorarioRotativo], cw.[WebUserZafrales], cw.[WebUserLibretaConducir], cw.[WebUserCv],
       cw.[WebUserFechaAct], ec.[EstadoCivilDescripcion],
       c.[CandidatoId], e.[UltimaEntrevista], a.[Asignado]
FROM [CandidatosWeb] cw
LEFT JOIN [Departamentos] d ON d.[DepartamentoId] = cw.[DepartamentoId]
LEFT JOIN [Localidades] l ON l.[LocalidadId] = cw.[LocalidadId]
LEFT JOIN [EstadosCiviles] ec ON ec.[EstadoCivilId] = cw.[WebUserEstadoCivilId]
LEFT JOIN [Candidatos] c ON c.[WebUserId] = cw.[WebUserId]
-- entrevistas y asignaciones del candidato: se suman cuando armemos la consulta definitiva
"""


@lru_cache(maxsize=1)
def candidatos_web():
    r = random.Random(4860621)
    deptos, pesos = list(DEPARTAMENTOS), list(DEPARTAMENTOS.values())
    filas = []
    for i in range(2400):
        sexo = r.choices(["F", "M"], weights=[55, 45])[0]
        nombre = r.choice(NOMBRES_F if sexo == "F" else NOMBRES_M)
        apellido = r.choice(APELLIDOS)
        edad = max(18, min(64, int(r.gauss(30, 9))))
        depto = r.choices(deptos, weights=pesos)[0] if r.random() > .04 else ""
        localidad = r.choice(LOCALIDADES[depto]) if depto in LOCALIDADES and r.random() > .1 else ""
        # Más actualizaciones recientes: el portal tiene cada vez más uso
        dias_act = int((r.random() ** 1.3) * 1100)

        desempleado = r.random() < .38
        base = r.gauss(32000 + (edad - 18) * 900, 9000)
        actual = 0 if desempleado else max(19000, round(base, -3))
        aspirado = max(21000, round((actual or base) * r.uniform(1.05, 1.45), -3))
        if r.random() < .06:
            aspirado = 0  # no lo completó

        cv = r.random() < .45 + (.2 if dias_act < 365 else 0)
        completo = sum([bool(depto), cv, aspirado > 0])
        # Probabilidad de avanzar: mejor perfil y registros más recientes avanzan más
        p1 = .06 + completo * .12 + (.08 if dias_act < 365 else 0) + (.05 if depto in ("Montevideo", "Canelones") else 0)
        etapa = 0
        if r.random() < p1:
            etapa = 1
            if r.random() < .62:
                etapa = 2
                if r.random() < .36 + (.08 if 22 <= edad <= 40 else 0):
                    etapa = 3

        email_ok = r.random() > .07
        filas.append({
            "id": 100000 + i,
            "nombre": nombre, "apellido": apellido,
            "documento": r.randint(1_800_000, 6_400_000) if r.random() > .03 else None,
            "email": (f"{nombre}.{apellido}{r.randint(1, 99)}@ejemplo.com".lower()
                      .replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
                      if email_ok else ""),
            "celular": f"09{r.randint(1, 9)} {r.randint(100, 999)} {r.randint(100, 999)}" if r.random() > .05 else "",
            "departamento": depto, "localidad": localidad,
            "sexo": sexo, "edad": edad,
            "estado_civil": r.choices(list(ESTADOS_CIVILES), weights=list(ESTADOS_CIVILES.values()))[0],
            "salario_actual": actual, "salario_aspirado": aspirado,
            "moneda": "USD" if r.random() < .02 else "UYU",
            "disponibilidad": SI if r.random() < .64 else "N",
            "rotativo": SI if r.random() < .47 else "N",
            "zafrales": SI if r.random() < .52 else "N",
            "libreta": SI if r.random() < .31 else "N",
            "cv": cv,
            "fecha_act": hace(dias_act),
            "dias_act": dias_act,
            "etapa": etapa,
        })
    return tuple(filas)


def registros(periodo=None):
    """Registros, opcionalmente solo los actualizados en los últimos N días."""
    filas = candidatos_web()
    if periodo in (None, "todos"):
        return list(filas)
    dias = int(periodo)
    return [f for f in filas if f["dias_act"] <= dias]


# Columnas que se muestran en el modal de detalle
COLUMNAS_DETALLE = ["Id", "Nombre", "Documento", "Email", "Celular", "Departamento", "Edad", "Sexo",
                    "Salario aspirado", "Última actualización", "Etapa"]


def fila_detalle(f):
    from apps.core.utils import formato_pesos
    return [
        f["id"], f"{f['nombre']} {f['apellido']}", f["documento"] or "—", f["email"] or "—", f["celular"] or "—",
        f["departamento"] or "—", f["edad"], "Mujer" if f["sexo"] == "F" else "Hombre",
        (formato_pesos(f["salario_aspirado"]) + (" US$" if f["moneda"] == "USD" else "")) if f["salario_aspirado"] else "—",
        f["fecha_act"].strftime("%d/%m/%Y"), ETAPAS[f["etapa"]],
    ]


def resumen_landing():
    todos = candidatos_web()
    return [
        {"valor": f"{len(todos):,}".replace(",", "."), "texto": "registrados"},
        {"valor": sum(1 for f in todos if f["dias_act"] <= 30), "texto": "actualizados en 30 días"},
    ]
