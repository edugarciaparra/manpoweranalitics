"""
Validación de las consultas que arma el modelo antes de ejecutarlas.

Se acepta solo una sentencia SELECT (con o sin WITH) sobre las tablas
permitidas, sin columnas personales y sin funciones que salgan de la base.
Además conviene que el usuario de la conexión tenga solo permiso de lectura
(rol db_datareader): esta validación es una segunda barrera, no la única.
"""
import sqlglot
from sqlglot import exp
from sqlglot.tokens import TokenType

from .esquema import TABLAS_PERMITIDAS, TABLAS_PERSONALES, columnas_bloqueadas, columnas_por_tabla, parece_personal


class ConsultaNoPermitida(ValueError):
    pass


PALABRAS_PROHIBIDAS = {
    "INSERT", "UPDATE", "DELETE", "MERGE", "DROP", "ALTER", "CREATE", "TRUNCATE", "EXEC", "EXECUTE",
    "GRANT", "REVOKE", "DENY", "INTO", "OPENROWSET", "OPENDATASOURCE", "OPENQUERY", "OPENXML", "BULK",
    "BACKUP", "RESTORE", "SHUTDOWN", "WAITFOR", "DBCC", "DECLARE", "SET", "USE", "KILL", "RECONFIGURE",
}
_PERMITIDAS = {t.lower() for t in TABLAS_PERMITIDAS}
_PERSONALES = {t.lower() for t in TABLAS_PERSONALES}
_NODOS_PROHIBIDOS = tuple(getattr(exp, n) for n in
                          ("Insert", "Update", "Delete", "Merge", "Drop", "Create", "Alter", "Command",
                           "Into", "Use", "Set", "Grant") if hasattr(exp, n))


def _sin_punto_y_coma_final(sql):
    sql = sql.strip()
    while sql.endswith(";"):
        sql = sql[:-1].rstrip()
    return sql


def validar(sql):
    """Devuelve el SQL listo para ejecutar o lanza ConsultaNoPermitida con el motivo."""
    sql = _sin_punto_y_coma_final(sql or "")
    if not sql:
        raise ConsultaNoPermitida("La consulta está vacía.")

    try:
        tokens = sqlglot.tokenize(sql, read="tsql")
    except sqlglot.errors.TokenError as e:
        raise ConsultaNoPermitida("La consulta tiene un texto sin cerrar.") from e
    for t in tokens:
        if t.token_type == TokenType.SEMICOLON:
            raise ConsultaNoPermitida("Solo se permite una sentencia.")
        if t.token_type not in (TokenType.STRING, TokenType.IDENTIFIER) and t.text.upper() in PALABRAS_PROHIBIDAS:
            raise ConsultaNoPermitida(f"No se permite {t.text.upper()}: solo consultas de lectura.")
        if t.token_type != TokenType.STRING and t.text.lower().startswith(("xp_", "sp_")):
            raise ConsultaNoPermitida("No se permiten procedimientos del sistema.")

    try:
        sentencias = sqlglot.parse(sql, read="tsql")
    except sqlglot.errors.ParseError as e:
        raise ConsultaNoPermitida(f"No se pudo interpretar la consulta: {str(e).splitlines()[0]}") from e
    sentencias = [s for s in sentencias if s is not None]
    if len(sentencias) != 1:
        raise ConsultaNoPermitida("Solo se permite una sentencia.")
    arbol = sentencias[0]

    if not isinstance(arbol, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise ConsultaNoPermitida("Solo se permiten consultas SELECT.")
    if any(True for _ in arbol.find_all(*_NODOS_PROHIBIDOS)):
        raise ConsultaNoPermitida("La consulta tiene una instrucción que no es de lectura.")

    ctes = {c.alias_or_name.lower() for c in arbol.find_all(exp.CTE)}
    tablas = set()
    alias = {}  # alias o nombre (minúscula) -> tabla (minúscula)
    for t in arbol.find_all(exp.Table):
        if not t.name:  # funciones con forma de tabla
            raise ConsultaNoPermitida("No se permiten funciones de tabla.")
        if t.catalog or (t.db and t.db.lower() != "dbo"):
            raise ConsultaNoPermitida("Solo se puede consultar la base sgo_new (esquema dbo).")
        nombre = t.name.lower()
        if nombre in ctes:
            continue
        if nombre not in _PERMITIDAS:
            raise ConsultaNoPermitida(f"La tabla {t.name} no está habilitada para consultas.")
        tablas.add(nombre)
        alias[nombre] = nombre
        if t.alias:
            alias[t.alias.lower()] = nombre

    bloqueadas = columnas_bloqueadas()
    con_personales = bool(tablas & _PERSONALES)
    # Columnas de las tablas no personales de la consulta (para resolver columnas sin alias)
    esquema = {t.lower(): {c.lower() for c, _ in cols} for t, cols in columnas_por_tabla().items()}
    de_otras = set().union(*(esquema.get(t, set()) for t in tablas - _PERSONALES))

    def es_personal(c):
        if not con_personales or not parece_personal(c.name):
            return False
        if c.table:
            return alias.get(c.table.lower()) in _PERSONALES
        return c.name.lower() not in de_otras

    for c in arbol.find_all(exp.Column):
        if c.name and (c.name.lower() in bloqueadas or es_personal(c)):
            raise ConsultaNoPermitida(f"La columna {c.name} tiene datos personales y no se puede consultar.")

    if con_personales:
        for select in arbol.find_all(exp.Select):
            for e in select.expressions:
                if isinstance(e, exp.Star) or (isinstance(e, exp.Column) and isinstance(e.this, exp.Star)):
                    raise ConsultaNoPermitida("Con tablas de candidatos hay que nombrar las columnas (sin *).")

    return sql
