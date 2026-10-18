"""
Datos del módulo Candidatos web (tabla [CandidatosWeb]).

Con la base conectada, candidatos_web() lee CONSULTA_SGO: los textos de
departamento, localidad y estado civil salen de sus tablas con JOIN, y la etapa
del proceso se arma cruzando con [Candidatos], [Entrevistas] y [Asignaciones].

Sin conexión se generan registros de ejemplo con semilla fija. Igual que la
tabla real, guardan solo los Id y las descripciones se buscan en las tablas
de referencia (apps/core/catalogos.py). Nombres, documentos, emails y
teléfonos de ejemplo son inventados.

Importante: la tabla no tiene fecha de alta. La única fecha es
WebUserFechaAct (última actualización del registro).
"""
import random
from datetime import date

from apps.core.cache import cache_temporal
from apps.core.catalogos import catalogo
from apps.core.db import consultar, sgo_configurada
from apps.core.utils import hace

# Valores de los campos de una letra. Ajustar cuando tengamos el resultado
# completo de la consulta de códigos.
SI = "S"

# Etapa a la que llegó cada registro web dentro de Manpower
ETAPAS = ["Solo registro web", "Pasó a candidato", "Entrevistado", "Ingresado"]

CONSULTA_SGO = """
SELECT cw.[WebUserId], cw.[WebUserNombre], cw.[WebUserApellido], cw.[WebUserNroDocumento],
       cw.[WebUserEmail], cw.[WebUserCelular], d.[DepartamentoNombre], l.[LocalidadNombre],
       cw.[WebUserSexo], cw.[WebUserFechaNacimiento], cw.[WebUserSalarioActual], cw.[WebUserSalarioAspirado],
       cw.[WebUserSalarioAspiradoMoneda], cw.[WebUserDisponibilidadHoraria], cw.[WebUserHorarioRotativo],
       cw.[WebUserZafrales], cw.[WebUserLibretaConducir], cw.[WebUserCv], cw.[WebUserFechaAct],
       ec.[EstadoCivilDescripcion],
       c.[CandidatoId],
       CASE WHEN e.[CandidatoId] IS NOT NULL THEN 1 ELSE 0 END AS Entrevistado,
       CASE WHEN a.[CandidatoId] IS NOT NULL THEN 1 ELSE 0 END AS Asignado
FROM [CandidatosWeb] cw
LEFT JOIN [Departamentos] d ON d.[DepartamentoId] = cw.[DepartamentoId]
LEFT JOIN [Localidades] l ON l.[LocalidadId] = cw.[LocalidadId]
LEFT JOIN [EstadosCiviles] ec ON ec.[EstadoCivilId] = cw.[WebUserEstadoCivilId]
LEFT JOIN (SELECT [WebUserId], MIN([CandidatoId]) AS CandidatoId
           FROM [Candidatos] WHERE [WebUserId] IS NOT NULL GROUP BY [WebUserId]) c ON c.[WebUserId] = cw.[WebUserId]
LEFT JOIN (SELECT DISTINCT [CandidatoId] FROM [Entrevistas]) e ON e.[CandidatoId] = c.[CandidatoId]
LEFT JOIN (SELECT DISTINCT [CandidatoId] FROM [Asignaciones]) a ON a.[CandidatoId] = c.[CandidatoId]
"""


def _texto(v):
    return (v or "").strip() if isinstance(v, str) else v


def _edad(nacimiento):
    if not nacimiento:
        return 0
    n = nacimiento.date() if hasattr(nacimiento, "date") else nacimiento
    hoy = date.today()
    return hoy.year - n.year - ((hoy.month, hoy.day) < (n.month, n.day))


def _desde_sgo():
    hoy = date.today()
    filas = []
    for r in consultar(CONSULTA_SGO):
        act = r["WebUserFechaAct"].date() if hasattr(r["WebUserFechaAct"], "date") else r["WebUserFechaAct"]
        etapa = 3 if r["Asignado"] else 2 if r["Entrevistado"] else 1 if r["CandidatoId"] else 0
        filas.append({
            "id": int(r["WebUserId"]),
            "nombre": _texto(r["WebUserNombre"]), "apellido": _texto(r["WebUserApellido"]),
            "documento": int(r["WebUserNroDocumento"]) if r["WebUserNroDocumento"] else None,
            "email": _texto(r["WebUserEmail"]), "celular": _texto(r["WebUserCelular"]),
            "departamento": _texto(r["DepartamentoNombre"]), "localidad": _texto(r["LocalidadNombre"]),
            "sexo": _texto(r["WebUserSexo"]), "edad": _edad(r["WebUserFechaNacimiento"]),
            "estado_civil": _texto(r["EstadoCivilDescripcion"]) or "Sin dato",
            "salario_actual": float(r["WebUserSalarioActual"] or 0),
            "salario_aspirado": float(r["WebUserSalarioAspirado"] or 0),
            "moneda": _texto(r["WebUserSalarioAspiradoMoneda"]) or "UYU",
            "disponibilidad": _texto(r["WebUserDisponibilidadHoraria"]),
            "rotativo": _texto(r["WebUserHorarioRotativo"]),
            "zafrales": _texto(r["WebUserZafrales"]),
            "libreta": _texto(r["WebUserLibretaConducir"]),
            "cv": bool(_texto(r["WebUserCv"])),
            "fecha_act": act, "dias_act": (hoy - act).days if act else 99999,
            "etapa": etapa,
        })
    return tuple(filas)


# --- Datos de ejemplo -------------------------------------------------------
_NOMBRES_F = ["María", "Lucía", "Sofía", "Valentina", "Camila", "Florencia", "Agustina", "Micaela", "Natalia",
              "Carolina", "Paula", "Andrea", "Gabriela", "Laura", "Victoria", "Martina", "Romina", "Silvia"]
_NOMBRES_M = ["Juan", "Martín", "Diego", "Pablo", "Nicolás", "Santiago", "Federico", "Gonzalo", "Matías",
              "Sebastián", "Bruno", "Rodrigo", "Andrés", "Facundo", "Joaquín", "Emiliano", "Marcelo", "Luis"]
_APELLIDOS = ["Rodríguez", "González", "Fernández", "Pérez", "García", "López", "Martínez", "Silva", "Sosa",
              "Díaz", "Pereira", "Suárez", "Romero", "Álvarez", "Ramos", "Acosta", "Benítez", "Núñez",
              "Cabrera", "Olivera", "Castro", "Méndez", "Ferreira", "Machado"]


def _ejemplo():
    r = random.Random(4860621)
    deptos = catalogo("Departamentos")
    locs = catalogo("Localidades")
    civiles = catalogo("EstadosCiviles")
    ids_depto = sorted(deptos)
    # Más registrados en los primeros departamentos de la tabla, como en la realidad
    pesos_depto = [max(1, 46 // (i + 1) ** 1.2) for i in range(len(ids_depto))]
    # Localidades de ejemplo: el Id indica el departamento (101 = depto 1, 201 = depto 2...)
    locs_por_depto = {}
    for lid in locs:
        locs_por_depto.setdefault(lid // 100, []).append(lid)
    ids_civil = sorted(civiles)

    filas = []
    for i in range(2400):
        sexo = r.choices(["F", "M"], weights=[55, 45])[0]
        nombre = r.choice(_NOMBRES_F if sexo == "F" else _NOMBRES_M)
        apellido = r.choice(_APELLIDOS)
        edad = max(18, min(64, int(r.gauss(30, 9))))
        depto_id = r.choices(ids_depto, weights=pesos_depto)[0] if r.random() > .04 else None
        loc_id = (r.choice(locs_por_depto[depto_id])
                  if depto_id in locs_por_depto and r.random() > .1 else None)
        dias_act = int((r.random() ** 1.3) * 1100)

        desempleado = r.random() < .38
        base = r.gauss(32000 + (edad - 18) * 900, 9000)
        actual = 0 if desempleado else max(19000, round(base, -3))
        aspirado = max(21000, round((actual or base) * r.uniform(1.05, 1.45), -3))
        if r.random() < .06:
            aspirado = 0

        cv = r.random() < .45 + (.2 if dias_act < 365 else 0)
        completo = sum([bool(depto_id), cv, aspirado > 0])
        p1 = .06 + completo * .12 + (.08 if dias_act < 365 else 0) + (.05 if depto_id in ids_depto[:2] else 0)
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
            # Descripciones tomadas de las tablas de referencia por Id (como el JOIN de la consulta real)
            "departamento": deptos.get(depto_id, ""), "localidad": locs.get(loc_id, ""),
            "sexo": sexo, "edad": edad,
            "estado_civil": civiles[r.choices(ids_civil, weights=[58, 22, 14, 5, 1][:len(ids_civil)])[0]],
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


@cache_temporal()
def candidatos_web():
    return _desde_sgo() if sgo_configurada() else _ejemplo()


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
