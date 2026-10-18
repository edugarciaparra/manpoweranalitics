"""
Datos del módulo Facturación.

Por ahora con datos de ejemplo. Al conectar sgo_new, se reemplaza el cuerpo
de cada función por la consulta a las órdenes de facturación.
"""
from apps.core.utils import ultimos_meses

# cliente: (sector, monto base mensual, crecimiento mensual, ranking)
CLIENTES = {
    "Antel": ("Telecomunicaciones", 560000, 0.012, "A"),
    "Tienda Inglesa": ("Retail", 360000, 0.010, "A"),
    "Ta-Ta": ("Retail", 270000, 0.004, "A"),
    "Conaprole": ("Industria", 190000, 0.002, "A"),
    "Disco": ("Retail", 150000, -0.025, "B"),
    "Farmashop": ("Retail", 60000, 0.045, "B"),
    "Cutcsa": ("Transporte", 85000, 0.000, "B"),
    "Copsa": ("Transporte", 70000, -0.030, "B"),
    "UTE": ("Energía", 95000, -0.018, "B"),
    "Zonamerica": ("Servicios", 48000, 0.006, "C"),
    "Pronto!": ("Servicios", 30000, 0.060, "C"),
}

# Estacionalidad del negocio (enero = índice 0): picos en diciembre y marzo
ESTACIONAL = [0.92, 0.88, 1.04, 1.00, 0.98, 0.95, 0.97, 0.99, 1.01, 1.03, 1.06, 1.17]

# Variación propia de cada mes para que la serie no sea perfecta
RUIDO = [1.00, 0.97, 1.03, 0.99, 1.02, 0.98, 1.01, 0.96, 1.04, 1.00, 0.98, 1.02,
         1.01, 0.99, 1.03, 0.97, 1.00, 1.02, 0.98, 1.01, 0.99, 1.03, 0.97, 1.00]


def facturacion_mensual():
    """{cliente: [monto por mes]} para los últimos 24 meses completos, y la lista de meses."""
    meses = ultimos_meses(25)[:-1]  # sin el mes en curso
    datos = {}
    for j, (cliente, (_, base, crec, _)) in enumerate(CLIENTES.items()):
        serie = []
        for i, (_, mes) in enumerate(meses):
            ruido = RUIDO[(i + j * 3) % len(RUIDO)]
            serie.append(round(base * (1 + crec) ** (i - 23) * ESTACIONAL[mes - 1] * ruido, -3))
        datos[cliente] = serie
    return meses, datos


def total_mensual():
    meses, datos = facturacion_mensual()
    return meses, [sum(v[i] for v in datos.values()) for i in range(len(meses))]


def resumen_landing():
    from apps.core.utils import formato_millones
    meses, total = total_mensual()
    _, datos = facturacion_mensual()
    en_baja = sum(1 for v in datos.values() if sum(v[-3:]) < sum(v[-6:-3]) * .97)
    return [
        {"valor": formato_millones(total[-1]), "texto": "último mes"},
        {"valor": en_baja, "texto": "clientes en baja", "alerta": True},
    ]
