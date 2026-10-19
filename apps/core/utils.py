"""Utilidades comunes a todos los módulos."""
from datetime import date, timedelta

PERIODOS = {
    "30": "Últimos 30 días",
    "90": "Últimos 90 días",
    "365": "Último año",
}
PERIODO_DEFECTO = "90"

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]


def hace(dias):
    """Fecha que cae `dias` días antes de hoy."""
    return date.today() - timedelta(days=dias)


def leer_periodo(request):
    periodo = request.GET.get("periodo", PERIODO_DEFECTO)
    return periodo if periodo in PERIODOS else PERIODO_DEFECTO


def desde_periodo(periodo):
    return hace(int(periodo))


def ultimos_meses(n=6):
    """Lista de (anio, mes) de los últimos n meses, del más viejo al actual."""
    hoy = date.today()
    resultado = []
    anio, mes = hoy.year, hoy.month
    for _ in range(n):
        resultado.append((anio, mes))
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    return list(reversed(resultado))


def contar_por_mes(filas, meses, campo="fecha", filtro=None):
    """Cuenta filas por (anio, mes) de su fecha, para los meses pedidos."""
    conteo = {m: 0 for m in meses}
    for f in filas:
        if filtro and not filtro(f):
            continue
        clave = (f[campo].year, f[campo].month)
        if clave in conteo:
            conteo[clave] += 1
    return [conteo[m] for m in meses]


def meses_completos(n):
    """Los últimos n meses terminados (sin el mes en curso)."""
    return ultimos_meses(n + 1)[:-1]


def siguientes_meses(desde, n):
    """Los n meses posteriores a (anio, mes)."""
    anio, mes = desde
    resultado = []
    for _ in range(n):
        mes += 1
        if mes == 13:
            anio, mes = anio + 1, 1
        resultado.append((anio, mes))
    return resultado


def etiqueta_mes(anio, mes):
    return f"{MESES[mes - 1]} {str(anio)[2:]}"


def formato_numero(valor):
    """1234567 -> '1.234.567' (formato uruguayo)."""
    return f"{valor:,.0f}".replace(",", ".")


def formato_pesos(valor):
    #   = espacio que no corta línea: "$" y el número quedan juntos
    return f"$ {formato_numero(valor)}"


def formato_pct(valor, signo=False, decimales=1):
    """5.04 -> '5%', 7.36 -> '7,4%'. Con signo=True agrega '+' a los positivos."""
    redondeado = round(valor, decimales)
    if redondeado == int(redondeado):
        texto = f"{int(redondeado)}"
    else:
        texto = f"{redondeado:.{decimales}f}".replace(".", ",")
    if signo and valor > 0:
        texto = "+" + texto
    return texto.replace("-", "−") + "%"


def formato_millones(valor):
    """1530000 -> '$ 1,5 M'. Para valores chicos usa formato_pesos."""
    if valor < 1_000_000:
        return formato_pesos(valor)
    return f"$ {valor / 1_000_000:.1f} M".replace(".", ",")
