"""Cache en memoria con vencimiento, para no consultar la base en cada pantalla."""
import time
from functools import wraps

MINUTOS_CACHE = 15


def cache_temporal(segundos=MINUTOS_CACHE * 60):
    """Guarda el resultado de una función sin argumentos durante `segundos`."""
    def decorador(funcion):
        estado = {"hasta": 0, "valor": None}

        @wraps(funcion)
        def envoltura():
            ahora = time.monotonic()
            if ahora >= estado["hasta"]:
                estado["valor"] = funcion()
                estado["hasta"] = ahora + segundos
            return estado["valor"]

        envoltura.limpiar = lambda: estado.update(hasta=0)
        return envoltura
    return decorador
