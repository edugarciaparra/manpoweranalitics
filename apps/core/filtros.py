"""
Filtros de las pantallas (divisiones, estado, fechas, ...), como en el SGO.

Un análisis declara sus filtros al registrarse:

    FILTROS = [
        Filtro.varios("divisiones_ids", "Divisiones", "Divisiones"),
        Filtro.uno("estado_id", "Estado", "EstadosPedido"),
        Filtro.fecha("fecha_desde", "Desde"),
        Filtro.fecha("fecha_hasta", "Hasta"),
        Filtro.fijo("meses_tendencia", "Meses de tendencia", {"6": "6", "12": "12", "24": "24"}, "12"),
    ]

    @catalogo.registrar("resumen", "Resumen", "...", filtros=FILTROS)
    def resumen(periodo, filtros):
        filtros["divisiones_ids"]  -> [3, 4]  (lista de int, vacía = todas)
        filtros["estado_id"]       -> 2 o None
        filtros["fecha_desde"]     -> date o None

Las opciones de los combos salen de la tabla de referencia (apps/core/catalogos.py).
Los valores se validan acá (enteros, fechas ISO), así los análisis los pueden
pasar como parámetros %s sin riesgo.
"""
from datetime import date


class Filtro:
    def __init__(self, nombre, etiqueta, tipo, tabla=None, opciones=None, defecto=None, ancho=2):
        self.nombre = nombre
        self.etiqueta = etiqueta
        self.tipo = tipo          # varios | uno | fecha | fijo | numero | texto
        self.tabla = tabla        # tabla de referencia de catalogos.py
        self._opciones = opciones
        self.defecto = defecto
        self.ancho = ancho

    @classmethod
    def varios(cls, nombre, etiqueta, tabla):
        return cls(nombre, etiqueta, "varios", tabla=tabla, ancho=12)

    @classmethod
    def uno(cls, nombre, etiqueta, tabla=None, opciones=None, defecto=None):
        return cls(nombre, etiqueta, "uno", tabla=tabla, opciones=opciones, defecto=defecto)

    @classmethod
    def fecha(cls, nombre, etiqueta, defecto=None):
        return cls(nombre, etiqueta, "fecha", defecto=defecto)

    @classmethod
    def fijo(cls, nombre, etiqueta, opciones, defecto):
        """Combo con opciones fijas (por ejemplo meses de tendencia o un umbral)."""
        return cls(nombre, etiqueta, "fijo", opciones=opciones, defecto=defecto)

    @classmethod
    def numero(cls, nombre, etiqueta, defecto):
        return cls(nombre, etiqueta, "numero", defecto=defecto)

    @classmethod
    def texto(cls, nombre, etiqueta):
        """Texto libre para buscar (se pasa siempre como parámetro %s)."""
        return cls(nombre, etiqueta, "texto", ancho=3)

    def opciones(self):
        """[(valor, texto), ...] ordenado por texto."""
        if self._opciones is not None:
            return [(str(k), v) for k, v in self._opciones.items()]
        if self.tabla:
            from .catalogos import catalogo
            try:
                return sorted(((str(k), v) for k, v in catalogo(self.tabla).items()), key=lambda x: x[1].lower())
            except Exception:  # noqa: BLE001  (tabla sin datos o sin conexión)
                return []
        return []

    # --- lectura y validación -------------------------------------------
    def leer(self, querydict):
        if self.tipo == "varios":
            return [int(v) for v in querydict.getlist(self.nombre) if str(v).strip().lstrip("-").isdigit()]
        crudo = (querydict.get(self.nombre) or "").strip()
        if self.tipo == "fecha":
            try:
                return date.fromisoformat(crudo[:10]) if crudo else self._defecto_fecha()
            except ValueError:
                return self._defecto_fecha()
        if self.tipo == "fijo":
            validas = {str(k) for k in self._opciones}
            return crudo if crudo in validas else self.defecto
        if self.tipo == "texto":
            return crudo[:80] or None
        if self.tipo == "numero":
            try:
                return int(crudo) if crudo else self.defecto
            except ValueError:
                return self.defecto
        # uno
        if self._opciones is not None and not self.tabla:
            return crudo if crudo in {str(k) for k in self._opciones} else self.defecto
        return int(crudo) if crudo.lstrip("-").isdigit() else self.defecto

    def _defecto_fecha(self):
        return self.defecto() if callable(self.defecto) else self.defecto


def leer_filtros(definiciones, querydict):
    return {f.nombre: f.leer(querydict) for f in definiciones or []}


def para_plantilla(definiciones, valores):
    """Lo que necesita la plantilla para dibujar la barra de filtros."""
    salida = []
    for f in definiciones or []:
        v = valores.get(f.nombre)
        if f.tipo == "varios":
            elegidos = {str(x) for x in v or []}
        elif f.tipo == "fecha":
            elegidos = {v.isoformat()} if v else set()
        else:
            elegidos = {str(v)} if v not in (None, "") else set()
        salida.append({
            "nombre": f.nombre, "etiqueta": f.etiqueta, "tipo": f.tipo, "ancho": f.ancho,
            "opciones": [{"valor": k, "texto": t, "elegido": k in elegidos} for k, t in f.opciones()],
            "valor": next(iter(elegidos), ""),
            "cantidad": len(elegidos) if f.tipo == "varios" else None,
        })
    return salida


def activos(definiciones, valores):
    """Cantidad de filtros con un valor distinto del de por defecto (para el botón)."""
    n = 0
    for f in definiciones or []:
        v = valores.get(f.nombre)
        if f.tipo == "varios":
            n += bool(v)
            continue
        defecto = f._defecto_fecha() if f.tipo == "fecha" else f.defecto
        if v not in (None, "") and v != defecto:
            n += 1
    return n
