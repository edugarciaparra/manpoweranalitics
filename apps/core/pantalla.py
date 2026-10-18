"""
Piezas comunes para armar las pantallas migradas del SGO: indicadores,
formatos y frases de lectura a partir de las filas de una consulta.
"""
from .sgo import num
from .utils import formato_numero, formato_pct


def entero(v):
    return formato_numero(num(v))


def pct(v):
    return formato_pct(num(v))


def decimal(v, decimales=1):
    return f"{num(v):.{decimales}f}".replace(".", ",")


def dias(v):
    return f"{decimal(v)} días"


def kpi(label, valor, detalle="", ayuda="", alerta=False):
    return {"label": label, "valor": valor, "detalle": detalle, "ayuda": ayuda, "alerta": alerta}


def total(filas, campo):
    return sum(num(f.get(campo)) for f in filas)


def proporcion(parte, todo):
    return num(parte) / num(todo) * 100 if num(todo) else 0


def lider(filas, campo_etiqueta, campo_valor, unidad="", que="el total"):
    """'X encabeza con N unidad (P% de el total).'"""
    if not filas:
        return ""
    t = total(filas, campo_valor)
    f = max(filas, key=lambda r: num(r.get(campo_valor)))
    v = num(f.get(campo_valor))
    return (f"{f.get(campo_etiqueta) or 'Sin dato'} encabeza con {formato_numero(v)} {unidad}".rstrip()
            + (f" ({formato_pct(proporcion(v, t))} de {que})." if t else "."))


def concentracion(filas, campo_valor, n=3, que="registros"):
    """'Los 3 primeros concentran el P% de los registros.'"""
    if len(filas) <= n:
        return ""
    t = total(filas, campo_valor)
    arriba = sum(sorted((num(f.get(campo_valor)) for f in filas), reverse=True)[:n])
    return f"Los {n} primeros concentran el {formato_pct(proporcion(arriba, t))} de los {que}." if t else ""


def extremos(filas, campo_etiqueta, campo_valor, formato=pct, mayor="más alto", menor="más bajo"):
    """'El más alto es X (v) y el más bajo Y (v).'"""
    validas = [f for f in filas if f.get(campo_valor) is not None]
    if len(validas) < 2:
        return ""
    alto = max(validas, key=lambda r: num(r.get(campo_valor)))
    bajo = min(validas, key=lambda r: num(r.get(campo_valor)))
    return (f"El {mayor} es {alto.get(campo_etiqueta)} ({formato(alto.get(campo_valor))}) y el {menor} "
            f"{bajo.get(campo_etiqueta)} ({formato(bajo.get(campo_valor))}).")


def etiquetas(filas, campo="label"):
    return [str(f.get(campo) if f.get(campo) not in (None, "") else "Sin dato").strip() for f in filas]


def valores(filas, campo):
    return [num(f.get(campo), None) for f in filas]


def tabla(titulo, columnas, filas, vacio="No hay datos para los filtros elegidos."):
    return {"titulo": titulo, "columnas": columnas, "filas": filas, "vacio": vacio}


def detalle(titulo, columnas, filas_dict, descripcion=""):
    """Respuesta del modal de registros a partir de las filas de una consulta."""
    claves = list(filas_dict[0].keys()) if filas_dict else []
    return {
        "titulo": titulo,
        "descripcion": descripcion,
        "columnas": columnas,
        "filas": [[f.get(k) for k in claves] for f in filas_dict],
    }


def meses_atras(fecha, meses):
    """La misma fecha `meses` meses antes (si el día no existe, el último día de ese mes)."""
    import calendar
    total = fecha.year * 12 + fecha.month - 1 - meses
    anio, mes = divmod(total, 12)
    dia = min(fecha.day, calendar.monthrange(anio, mes + 1)[1])
    return fecha.replace(year=anio, month=mes + 1, day=dia)
