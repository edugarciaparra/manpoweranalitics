"""
Datos del módulo Candidatos web (tabla [CandidatosWeb]).

Con la base conectada, candidatos_web() lee CONSULTA_SGO: los textos de
departamento, localidad y estado civil salen de sus tablas con JOIN, y la etapa
del proceso se arma cruzando con [Candidatos], [Entrevistas] y [Asignaciones].

Importante: la tabla no tiene fecha de alta. La única fecha es
WebUserFechaAct (última actualización del registro).
"""
from datetime import date

from apps.core.cache import cache_temporal
from apps.core.db import consultar

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


@cache_temporal()
def candidatos_web():
    return _desde_sgo()


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
