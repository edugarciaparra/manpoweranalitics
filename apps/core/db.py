"""
Acceso a la base de Manpower (alias "sgo").

Los módulos consultan con consultar(), que devuelve una lista de dicts:

    filas = consultar("SELECT TOP 10 [PedidoNumero] FROM [Pedidos] WHERE [EstadoPedidoId] = %s", [1])
    filas[0]["PedidoNumero"]

Siempre pasar los valores como parámetros (%s), nunca armando el texto del SQL.
"""
from django.conf import settings
from django.db import connections

ALIAS = "sgo"

# Solo para las pruebas automáticas: una función (sql, params) -> filas que
# reemplaza a la base. En el portal siempre es None y se consulta la base real.
SUSTITUTO_PRUEBAS = None


class BaseNoDisponible(RuntimeError):
    """No hay conexión configurada o la base no respondió."""


def sgo_configurada():
    return SUSTITUTO_PRUEBAS is not None or ALIAS in settings.DATABASES


def consultar(sql, params=None):
    if SUSTITUTO_PRUEBAS is not None:
        return SUSTITUTO_PRUEBAS(sql, params or [])
    if ALIAS not in settings.DATABASES:
        raise BaseNoDisponible("El portal no está conectado a la base de Manpower: completá SGO_DB_HOST en el archivo .env "
                               "y reiniciá el servidor.")
    with connections[ALIAS].cursor() as cursor:
        cursor.execute(sql, params or [])
        columnas = [c[0] for c in cursor.description]
        return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def consultar_valor(sql, params=None):
    """Para consultas que devuelven un solo número (COUNT, SUM, ...)."""
    filas = consultar(sql, params)
    return next(iter(filas[0].values())) if filas else None


class SoloLecturaSgoRouter:
    """Las tablas de Django (sesiones, usuarios, admin) van siempre a "default".
    Nunca se migra nada en la base de Manpower."""

    def db_for_read(self, model, **hints):
        return "default"

    def db_for_write(self, model, **hints):
        return "default"

    def allow_migrate(self, db, app_label, **hints):
        return db == "default"
