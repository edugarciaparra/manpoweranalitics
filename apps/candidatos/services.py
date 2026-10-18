"""
Piezas comunes de las pantallas de Candidatos (migradas de apps/analitica del SGO).

Los filtros son los del SGO (perfil, país, departamento, sexo, ...) y van
como parámetros. Las búsquedas de texto usan CHARINDEX para no escribir % en el SQL.
"""
from apps.core import sgo
from apps.core.filtros import Filtro

F_PERFIL = Filtro.uno("perfil_id", "Perfil", "PerfilesCandidatos")
F_PAIS = Filtro.uno("pais_id", "País de residencia", "Paises")
F_DEPTO = Filtro.uno("departamento_id", "Departamento", "Departamentos")
F_SEXO = Filtro.uno("sexo", "Sexo", opciones={"M": "Masculino", "F": "Femenino"})
F_ASIGNABLE = Filtro.uno("asignable", "Asignable", opciones={"si": "Asignables", "no": "No asignables"})
F_NIVEL = Filtro.uno("nivel_educativo_id", "Nivel educativo", "NivelesEducativos")
F_LIBRETA = Filtro.uno("tiene_libreta", "Libreta de conducir", opciones={"si": "Con libreta", "no": "Sin libreta"})
F_PSICOLOGO = Filtro.uno("psicologo_id", "Psicólogo", "Psicologos")
F_EXPERIENCIA = Filtro.uno("tiene_experiencia", "Entrevistas", opciones={"si": "Con entrevistas", "no": "Sin entrevistas"})

EDAD = "DATEDIFF(YEAR, c.CandidatoFechaNacimiento, GETDATE())"
NOMBRE = "RTRIM(c.CandidatoNombre) + ' ' + RTRIM(c.CandidatoApellido)"
DESEMPENO = "CASE WHEN c.CandidatoPromedioDesemGral > 0 THEN CAST(c.CandidatoPromedioDesemGral AS FLOAT) END"


def where(filtros, alias="c"):
    a = alias
    condiciones, params = ["1=1"], []
    for clave, columna in (("perfil_id", "PerfilCandidatoId"), ("pais_id", "CandidatoResidenciaId"),
                           ("departamento_id", "CandidatoDepartamentoId"), ("nivel_educativo_id", "NivelEducativoId")):
        if filtros.get(clave) is not None:
            condiciones.append(f"{a}.{columna} = %s")
            params.append(filtros[clave])
    if filtros.get("sexo"):
        condiciones.append(f"{a}.CandidatoSexo = %s")
        params.append(filtros["sexo"])
    if filtros.get("asignable"):
        condiciones.append(f"{a}.CandidatoNoAsignable = %s")
        params.append("S" if filtros["asignable"] == "no" else "N")
    if filtros.get("tiene_libreta") == "si":
        condiciones.append(f"{a}.CandidatoLibretaConducir = 'S'")
    elif filtros.get("tiene_libreta") == "no":
        condiciones.append(f"({a}.CandidatoLibretaConducir = 'N' OR {a}.CandidatoLibretaConducir IS NULL)")
    if filtros.get("tiene_experiencia") == "si":
        condiciones.append(f"EXISTS (SELECT 1 FROM dbo.Entrevistas ex WHERE ex.CandidatoId = {a}.CandidatoId)")
    elif filtros.get("tiene_experiencia") == "no":
        condiciones.append(f"NOT EXISTS (SELECT 1 FROM dbo.Entrevistas ex WHERE ex.CandidatoId = {a}.CandidatoId)")
    return " AND ".join(condiciones), params


def contiene(columna, texto):
    """Condición 'la columna contiene el texto' sin usar LIKE '%...%'."""
    return f"CHARINDEX('{texto}', {columna}) > 0"


COLUMNAS_CANDIDATO = ["Candidato Id", "Candidato", "Perfil", "País", "Nivel educativo", "Edad", "Asignable"]


def candidatos(filtros, condicion="", params=None, joins="", orden="c.CandidatoApellido, c.CandidatoNombre"):
    """Hasta 500 candidatos con los filtros de la pantalla y una condición más."""
    w, p = where(filtros)
    sql = f"""
        SELECT TOP 500 c.CandidatoId, {NOMBRE} AS candidato, RTRIM(pc.PerfilCandidatoDescripcion) AS perfil,
               RTRIM(pa.PaisNombre) AS pais, RTRIM(ne.NivelEducativoDescripcion) AS nivel,
               CASE WHEN {EDAD} BETWEEN 15 AND 90 THEN {EDAD} END AS edad,
               CASE WHEN c.CandidatoNoAsignable = 'S' THEN 'No' ELSE 'Sí' END AS asignable
        FROM dbo.Candidatos c
        LEFT JOIN dbo.PerfilesCandidatos pc ON c.PerfilCandidatoId = pc.PerfilCandidatoId
        LEFT JOIN dbo.Paises pa ON c.CandidatoResidenciaId = pa.PaisId
        LEFT JOIN dbo.NivelesEducativos ne ON c.NivelEducativoId = ne.NivelEducativoId
        {joins}
        WHERE {w} {f'AND ({condicion})' if condicion else ''}
        ORDER BY {orden}"""
    return sgo.filas(sql, p + list(params or []))


def resumen_landing():
    try:
        f = sgo.fila("""SELECT COUNT(*) AS total, SUM(CASE WHEN c.CandidatoNoAsignable = 'N' THEN 1 ELSE 0 END) AS asignables
                        FROM dbo.Candidatos c""")
    except Exception:  # noqa: BLE001
        return []
    return [{"valor": sgo.num(f.get("total")), "texto": "candidatos"},
            {"valor": sgo.num(f.get("asignables")), "texto": "asignables"}]
