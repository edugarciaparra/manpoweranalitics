"""
Consultas de las pantallas migradas del SGO.

    filas = sgo.filas(sql, params)      lista de dicts
    fila  = sgo.fila(sql, params)       un dict (o {} si no hay filas)
    valor = sgo.valor(sql, params)      el primer valor de la primera fila

Con la base conectada ejecutan el SQL tal cual (con parámetros %s). Sin
conexión devuelven filas de ejemplo con las mismas columnas que la consulta:
los nombres de columna se leen del propio SQL y los valores se inventan según
el nombre (meses para "mes", porcentajes para "pct", etc.). Así cada pantalla
se puede ver y probar sin la base; los números de ejemplo no significan nada.
"""
import hashlib
import random
import re
from datetime import date, timedelta

from .db import consultar, sgo_configurada

_NUMERICAS = re.compile(
    r"total|cant|count|value|valor|num|vacante|pedido|cubiert|asign|entrevist|candidat|monto|importe|"
    r"suma|sum|avg|prom|media|dias|días|horas|score|puntaje|edad|anios|años|meses|minimo|maximo|min_|max_|"
    r"orden|factur|viatic|personas|cumpl|cliente_?s$|unicos|únicos|tasa|pct|porc|ratio|indice|índice|z_|"
    r"desvio|std|riesgo|nivel|cantidad|frecuencia|ranking|rank|n$|^n_|^q_|tiempo|duracion|duración",
    re.IGNORECASE)
_PORCENTAJE = re.compile(r"pct|porc|tasa|ratio|cumplimiento|%|share|participacion|participación|efectividad|conversion", re.I)
_DIAS = re.compile(r"dias|días|tiempo|duracion|duración|demora|horas|lead|edad|anios|años|meses", re.I)
_DINERO = re.compile(r"monto|importe|factur|viatic|total_\w*(pesos|usd|monto)|ticket|ingreso|precio|costo", re.I)
_MES = re.compile(r"^(mes|periodo|período|anio_mes|año_mes|yyyymm|mes_anio)$|_mes$|^mes_", re.I)
_FECHA = re.compile(r"fecha|^fch|_fch|ultim[oa]|primer[oa]|desde|hasta|ingreso$|egreso$", re.I)
_ANIO = re.compile(r"^(anio|año|year)$", re.I)
_DIA_SEMANA = re.compile(r"dia_semana|día_semana|dia_orden|weekday|dow", re.I)
_TEXTO_PISTA = re.compile(r"label|nombre|descrip|dsc|cliente$|division|estado|tipo|perfil|canal|psicolog|"
                          r"responsable|ejecutivo|servicio|moneda|segmento|categoria|categoría|cargo|motivo|"
                          r"causal|departamento|localidad|sexo|rango|tramo|grupo|nivel_?texto|clasificacion|"
                          r"texto|palabra|observ|detalle|comentario|semaforo|alerta|bucket|franja", re.I)

_POZOS = {
    "cliente": ["Comercial del Sur", "Industrias Oriental", "Logística Atlántica", "Grupo Rioplatense",
                "Laboratorios Andina", "Distribuidora Central", "Servicios del Plata", "Tecno del Norte",
                "Alimentos Andina", "Transportes del Este", "Frigorífico Oriental", "Banco Atlántico"],
    "division": ["Industrial", "Administrativa", "Profesional", "Promociones", "Logística", "RPO",
                 "Experis", "Retail"],
    "estado": ["En proceso", "Cubierto", "Finalizado", "Cancelado", "No cubierto", "Abierto"],
    "psicolog": ["L. Sosa", "M. Fernández", "C. Pereira", "V. López", "A. Rodríguez", "G. Silva"],
    "responsable": ["A. Rodríguez", "M. Fernández", "L. Sosa", "P. Martínez", "C. Pereira"],
    "ejecutivo": ["A. Rodríguez", "M. Fernández", "L. Sosa", "P. Martínez", "C. Pereira"],
    "canal": ["Web Manpower", "LinkedIn", "Computrabajo", "Referidos", "Gallito", "Redes sociales"],
    "perfil": ["Operario", "Administrativo", "Vendedor", "Chofer", "Analista", "Promotor", "Cajero"],
    "tipo": ["Temporal", "Efectivo", "Eventual", "Zafral"],
    "servicio": ["Trabajo temporal", "Selección", "RPO", "Outsourcing", "Evaluación"],
    "moneda": ["Pesos", "Dólares"],
    "departamento": ["Montevideo", "Canelones", "Maldonado", "San José", "Colonia", "Paysandú", "Salto"],
    "localidad": ["Centro", "Pocitos", "Cordón", "Las Piedras", "Pando", "Ciudad de la Costa"],
    "sexo": ["F", "M"],
    "segmento": ["VIP", "Activo", "Riesgo", "Inactivo"],
    "motivo": ["Fin de contrato", "Renuncia", "Despido", "Fin de zafra", "Mejor oferta"],
    "causal": ["Fin de contrato", "Renuncia", "Despido", "Fin de zafra", "Mejor oferta"],
    "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
    "rango": ["0-7 días", "8-15 días", "16-30 días", "31-60 días", "Más de 60 días"],
    "tramo": ["0-7 días", "8-15 días", "16-30 días", "31-60 días", "Más de 60 días"],
    "nivel": ["Primaria", "Ciclo básico", "Bachillerato", "UTU", "Terciario", "Universitario"],
    "marca": ["Manpower", "Experis", "ManpowerGroup Solutions", "Talent Solutions"],
    "linea": ["Staffing", "Selección", "Outsourcing", "Consultoría", "RPO"],
    "practice": ["Finanzas", "IT", "Ingeniería", "Ventas", "Logística"],
    "centro": ["Montevideo Centro", "Zona Franca", "Interior", "Punta del Este", "Ciudad Vieja"],
    "sector": ["Comercio", "Industria", "Logística", "Servicios", "Salud", "Agro"],
    "semaforo": ["Verde", "Amarillo", "Rojo"],
}


_NUMERICAS_AGREGADAS = set()

# Para la columna "label" de ejemplo se elige el pozo según la tabla que describe
_PISTAS_LABEL = [
    ("ClienteNombre", "cliente"), ("ClienteRazonSocial", "cliente"), ("DivisionDescripcion", "division"),
    ("EstadoPedidoDescripcion", "estado"), ("EstadoAsignacionDescripcion", "estado"),
    ("Psicologo", "psicolog"), ("EjecutivoCuenta", "ejecutivo"), ("OrdenResponsable", "responsable"),
    ("CanalPublicacion", "canal"), ("PerfilCandidato", "perfil"), ("TipoPedido", "tipo"), ("TipoAsignacion", "tipo"),
    ("ServicioDescripcion", "servicio"), ("mondsc", "moneda"), ("Departamento", "departamento"),
    ("Localidad", "localidad"), ("CausalBaja", "causal"), ("Sexo", "sexo"), ("Segmento", "segmento"),
    ("NivelEducativo", "nivel"), ("Marca", "marca"), ("Linea", "linea"), ("PracticeArea", "practice"),
    ("CentroCosto", "centro"), ("SectorActividad", "sector"),
]


def _pozo_label(sql):
    for pista, clave in _PISTAS_LABEL:
        if pista.lower() in sql.lower():
            return _POZOS.get(clave)
    return None


def _alias(sql):
    """Nombres de las columnas que devuelve la consulta, en orden."""
    try:
        import sqlglot
        from sqlglot import exp
        arbol = sqlglot.parse_one(sql.replace("%s", "0"), read="tsql")
        select = arbol if isinstance(arbol, exp.Select) else arbol.find(exp.Select)
        nombres = []
        _NUMERICAS_AGREGADAS.clear()
        for e in select.expressions:
            nombre = e.alias_or_name or e.sql(dialect="tsql")
            nombres.append(nombre)
            # Agregados (COUNT, SUM, AVG, ROUND...) devuelven números
            interior = e.this if isinstance(e, exp.Alias) else e
            es_numero = isinstance(interior, exp.Literal) and not interior.is_string
            if interior.find(exp.AggFunc) or isinstance(interior, exp.Round) or es_numero:
                _NUMERICAS_AGREGADAS.add(nombre)
        top = select.args.get("limit")
        cantidad = None
        if top is not None:
            try:
                cantidad = int(top.expression.name if hasattr(top, "expression") else top.name)
            except (TypeError, ValueError, AttributeError):
                cantidad = None
        agrupa = bool(select.args.get("group")) or bool(select.args.get("order"))
        agregado = any(e.find(exp.AggFunc) for e in select.expressions)
        return nombres, cantidad, agrupa, agregado
    except Exception:  # noqa: BLE001
        nombres = re.findall(r"\bAS\s+\[?([A-Za-zÁÉÍÓÚáéíóúñÑ_][\wÁÉÍÓÚáéíóúñÑ]*)\]?", sql, re.I)
        return nombres or ["label", "value"], None, True, False


def _pozo(nombre):
    n = nombre.lower()
    for clave, valores in _POZOS.items():
        if clave in n:
            return valores
    return None


def _ejemplo(sql, params):
    nombres, top, agrupa, agregado = _alias(sql)
    numericas = set(_NUMERICAS_AGREGADAS)
    pozo_label = _pozo_label(sql)
    semilla = int(hashlib.md5((sql + repr(params)).encode()).hexdigest()[:8], 16)
    rnd = random.Random(semilla)
    base_n = rnd.uniform(80, 450)
    if agregado and not agrupa:
        n = 1
    else:
        n = min(top or rnd.randint(6, 12), 40)
    hoy = date.today().replace(day=1)
    meses = []
    a, m = hoy.year, hoy.month
    for _ in range(n):
        meses.append(f"{a}-{m:02d}")
        m -= 1
        if m == 0:
            a, m = a - 1, 12
    meses.reverse()

    filas = []
    for i in range(n):
        fila = {}
        for nombre in nombres:
            bajo = nombre.lower()
            if _MES.search(bajo):
                v = meses[i]
            elif _ANIO.search(bajo):
                v = hoy.year - (n - 1 - i)
            elif _DIA_SEMANA.search(bajo):
                v = _POZOS["dia_semana"][i % 7]
            elif bajo.endswith("id") or bajo in ("id", "numero", "número", "pedidonumero", "nro"):
                v = 1000 + i
            elif _FECHA.search(bajo) and not _NUMERICAS.search(bajo.replace("fecha", "")):
                v = (date.today() - timedelta(days=rnd.randint(0, 400))).strftime("%d/%m/%Y")
            elif bajo in ("label", "dsc", "descripcion", "nombre") and pozo_label and nombre not in numericas:
                v = pozo_label[i % len(pozo_label)] if i < len(pozo_label) else \
                    f"{pozo_label[i % len(pozo_label)]} {i // len(pozo_label) + 1}"
            elif nombre in numericas and not _PORCENTAJE.search(bajo) and not _DIAS.search(bajo) \
                    and not _DINERO.search(bajo):
                v = max(0, int(base_n * (1 - i / (n + 1)) * rnd.uniform(.85, 1)))
            elif (pozo := _pozo(bajo)) and not (_NUMERICAS.search(bajo) and not _TEXTO_PISTA.search(bajo)):
                v = pozo[i % len(pozo)] if i < len(pozo) else f"{pozo[i % len(pozo)]} {i // len(pozo) + 1}"
            elif _PORCENTAJE.search(bajo):
                v = round(rnd.uniform(35, 98), 1)
            elif _DINERO.search(bajo):
                v = round(rnd.uniform(20_000, 2_500_000) * (1 - i / (n + 2)), 0)
            elif _DIAS.search(bajo):
                v = round(rnd.uniform(3, 45), 1)
            elif _NUMERICAS.search(bajo):
                v = max(0, int(base_n * (1 - i / (n + 1)) * rnd.uniform(.85, 1)))
            elif _TEXTO_PISTA.search(bajo):
                v = f"{nombre.replace('_', ' ').capitalize()} {i + 1}"
            else:
                v = f"{nombre.replace('_', ' ').capitalize()} {i + 1}"
            fila[nombre] = v
        filas.append(fila)
    return filas


def filas(sql, params=None):
    if sgo_configurada():
        return consultar(sql, params or [])
    return _ejemplo(sql, params)


def fila(sql, params=None):
    r = filas(sql, params)
    return r[0] if r else {}


def valor(sql, params=None):
    r = fila(sql, params)
    return next(iter(r.values())) if r else None


def num(v, defecto=0):
    """Número (float o int) a partir de lo que devuelve la base (Decimal, None, ...)."""
    if v is None:
        return defecto
    try:
        f = float(v)
    except (TypeError, ValueError):
        return defecto
    return int(f) if f.is_integer() else f


def en_lista(nombre_columna, valores):
    """('col IN (%s, %s)', [v1, v2]) para filtros de varios valores."""
    marcas = ", ".join(["%s"] * len(valores))
    return f"{nombre_columna} IN ({marcas})", list(valores)
