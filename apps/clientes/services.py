"""
Datos del módulo Clientes.

Por ahora con datos de ejemplo. Al conectar sgo_new: [Clientes] cruzada con
la fecha del último pedido y lo facturado en el año.
"""
from apps.core.utils import hace

DIAS_SIN_ACTIVIDAD = 90


def clientes():
    # nombre, sector, activo, ranking, alta (días), último pedido (días), tendencia,
    # facturación anual, pedidos 12 meses, pedidos 12 meses anteriores
    filas = [
        ("Antel", "Telecomunicaciones", True, "A", 3100, 18, "Creciendo", 7_100_000, 58, 51),
        ("Tienda Inglesa", "Retail", True, "A", 2900, 12, "Creciendo", 4_600_000, 77, 70),
        ("Ta-Ta", "Retail", True, "A", 2600, 20, "Estable", 3_300_000, 67, 66),
        ("Conaprole", "Industria", True, "A", 3300, 41, "Estable", 2_300_000, 31, 33),
        ("Disco", "Retail", True, "B", 2400, 60, "Bajando", 1_650_000, 32, 45),
        ("UTE", "Energía", True, "B", 1900, 170, "Bajando", 1_050_000, 11, 19),
        ("Cutcsa", "Transporte", True, "B", 2000, 33, "Estable", 1_020_000, 14, 14),
        ("Copsa", "Transporte", True, "B", 1500, 130, "Bajando", 780_000, 13, 21),
        ("Farmashop", "Retail", True, "B", 300, 25, "Creciendo", 760_000, 8, 2),
        ("Zonamerica", "Servicios", True, "C", 800, 110, "Estable", 570_000, 5, 6),
        ("Pronto!", "Servicios", True, "C", 120, 9, "Creciendo", 420_000, 6, 0),
        ("Saman", "Industria", False, "C", 2200, 410, "Bajando", 0, 0, 4),
        ("Montes del Plata", "Industria", True, "B", 1400, 95, "Bajando", 640_000, 7, 12),
        ("Sabre", "Servicios", True, "C", 650, 44, "Estable", 310_000, 4, 4),
    ]
    return [
        {"nombre": n, "sector": s, "activo": a, "ranking": r, "fecha_alta": hace(alta),
         "dias_sin_pedir": ult, "tendencia": t, "facturacion": f, "pedidos_12m": p, "pedidos_prev": pp}
        for n, s, a, r, alta, ult, t, f, p, pp in filas
    ]


def activos():
    return [c for c in clientes() if c["activo"]]


def resumen_landing():
    act = activos()
    return [
        {"valor": len(act), "texto": "activos"},
        {"valor": sum(1 for c in act if c["dias_sin_pedir"] > DIAS_SIN_ACTIVIDAD),
         "texto": f"sin pedidos en {DIAS_SIN_ACTIVIDAD} días", "alerta": True},
    ]
