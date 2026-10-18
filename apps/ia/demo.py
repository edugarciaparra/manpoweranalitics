"""
Modo demostración (IA_PROVEEDOR=mock): respuestas armadas con los datos de
ejemplo para poder ver la pantalla sin clave de IA. Reconoce algunos temas
por palabras clave y muestra el SQL que se ejecutaría en la base real.
"""
import unicodedata
from collections import Counter

from .graficos import armar_grafico


def _normalizar(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def _clientes_por_sector():
    from apps.clientes.services import activos
    conteo = Counter(c["sector"] for c in activos())
    filas = [[s, n] for s, n in conteo.most_common()]
    return {
        "titulo": "Clientes activos por sector",
        "explicacion": "Cuenta los clientes en estado Activo agrupados por sector de actividad.",
        "sql": "SELECT sa.[SectorActividadDescripcion] AS [Sector], COUNT(*) AS [Clientes]\n"
               "FROM [Clientes] c\n"
               "JOIN [SectoresActividad] sa ON sa.[SectorActividadId] = c.[SectorActividadId]\n"
               "WHERE c.[EstadoClienteId] = 2\n"
               "GROUP BY sa.[SectorActividadDescripcion]\nORDER BY [Clientes] DESC",
        "columnas": ["Sector", "Clientes"], "filas": filas,
        "grafico": {"tipo": "barras_h", "x": "Sector", "y": ["Clientes"]},
        "respuesta": f"Hay {sum(conteo.values())} clientes activos. El sector con más clientes es "
                     f"{filas[0][0]} ({filas[0][1]}), seguido de {filas[1][0]} ({filas[1][1]}).\n"
                     f"- Los tres primeros sectores concentran {sum(f[1] for f in filas[:3])} clientes.",
    }


def _clientes_por_estado():
    from apps.clientes.services import clientes
    conteo = Counter(c["estado"] for c in clientes())
    filas = [[s, n] for s, n in conteo.most_common()]
    return {
        "titulo": "Clientes por estado",
        "explicacion": "Cuenta todos los clientes según su estado.",
        "sql": "SELECT ec.[EstadoClienteDescripcion] AS [Estado], COUNT(*) AS [Clientes]\n"
               "FROM [Clientes] c\n"
               "JOIN [EstadosCliente] ec ON ec.[EstadoClienteId] = c.[EstadoClienteId]\n"
               "GROUP BY ec.[EstadoClienteDescripcion]\nORDER BY [Clientes] DESC",
        "columnas": ["Estado", "Clientes"], "filas": filas,
        "grafico": {"tipo": "barras", "x": "Estado", "y": ["Clientes"]},
        "respuesta": f"De {sum(conteo.values())} clientes, {conteo.get('Activo', 0)} están activos. "
                     f"El estado más frecuente es {filas[0][0]} con {filas[0][1]} clientes.",
    }


def _top_facturacion():
    from apps.clientes.services import clientes
    top = sorted(clientes(), key=lambda c: -c["facturado_12m"])[:10]
    filas = [[c["razon_social"], round(c["facturado_12m"])] for c in top]
    return {
        "titulo": "Top 10 clientes por facturación (últimos 12 meses)",
        "explicacion": "Suma OrdenMonto de las órdenes de facturación de los últimos 12 meses por cliente.",
        "sql": "SELECT TOP 10 c.[ClienteRazonSocial] AS [Cliente], SUM(o.[OrdenMonto]) AS [Facturado]\n"
               "FROM [OrdenesFacturacion] o\n"
               "JOIN [Pedidos] p ON p.[PedidoId] = o.[PedidoId]\n"
               "JOIN [Clientes] c ON c.[ClienteId] = p.[ClienteId]\n"
               "WHERE o.[OrdenFecha] >= DATEADD(month, -12, GETDATE())\n"
               "GROUP BY c.[ClienteRazonSocial]\nORDER BY [Facturado] DESC",
        "columnas": ["Cliente", "Facturado"], "filas": filas,
        "grafico": {"tipo": "barras_h", "x": "Cliente", "y": ["Facturado"]},
        "respuesta": f"El cliente que más facturó en los últimos 12 meses es {filas[0][0]} "
                     f"($ {filas[0][1]:,.0f}).".replace(",", ".") +
                     f"\n- Entre los 10 primeros suman $ {sum(f[1] for f in filas):,.0f}.".replace(",", "."),
    }


def _candidatos_por_departamento():
    from apps.candidatosweb.services import candidatos_web
    conteo = Counter(c["departamento"] for c in candidatos_web())
    filas = [[d, n] for d, n in conteo.most_common(10)]
    return {
        "titulo": "Candidatos web por departamento",
        "explicacion": "Cuenta los registros de CandidatosWeb por departamento.",
        "sql": "SELECT TOP 10 d.[DepartamentoNombre] AS [Departamento], COUNT(*) AS [Candidatos]\n"
               "FROM [CandidatosWeb] cw\n"
               "LEFT JOIN [Departamentos] d ON d.[DepartamentoId] = cw.[DepartamentoId]\n"
               "GROUP BY d.[DepartamentoNombre]\nORDER BY [Candidatos] DESC",
        "columnas": ["Departamento", "Candidatos"], "filas": filas,
        "grafico": {"tipo": "barras_h", "x": "Departamento", "y": ["Candidatos"]},
        "respuesta": f"{filas[0][0]} concentra la mayor cantidad de candidatos web ({filas[0][1]}), "
                     f"seguido de {filas[1][0]} ({filas[1][1]}).",
    }


def _pedidos_por_mes():
    from apps.clientes.services import clientes
    # Con los datos de ejemplo se aproxima con la fecha del último pedido de cada cliente
    conteo = Counter(c["ultimo_pedido"].strftime("%Y-%m") for c in clientes() if c["ultimo_pedido"])
    filas = [[m, n] for m, n in sorted(conteo.items())][-12:]
    return {
        "titulo": "Pedidos por mes (últimos 12 meses)",
        "explicacion": "Cuenta los pedidos por mes según PedidoFecha.",
        "sql": "SELECT FORMAT(p.[PedidoFecha], 'yyyy-MM') AS [Mes], COUNT(*) AS [Pedidos]\n"
               "FROM [Pedidos] p\n"
               "WHERE p.[PedidoFecha] >= DATEADD(month, -12, GETDATE())\n"
               "GROUP BY FORMAT(p.[PedidoFecha], 'yyyy-MM')\nORDER BY [Mes]",
        "columnas": ["Mes", "Pedidos"], "filas": filas,
        "grafico": {"tipo": "lineas", "x": "Mes", "y": ["Pedidos"]},
        "respuesta": f"El mes con más pedidos fue {max(filas, key=lambda f: f[1])[0]}.",
    }


TEMAS = [
    (("factur", "vend", "ingres", "monto"), _top_facturacion),
    (("candidat", "postul", "departament"), _candidatos_por_departamento),
    (("mes", "evolu", "tendenc", "pedido"), _pedidos_por_mes),
    (("estado",), _clientes_por_estado),
    (("sector", "rubro", "cliente"), _clientes_por_sector),
]


def responder(pregunta):
    texto = _normalizar(pregunta)
    armar = next((f for claves, f in TEMAS if any(k in texto for k in claves)), _clientes_por_sector)
    r = armar()
    r["grafico"] = armar_grafico(r["grafico"], r["columnas"], r["filas"])
    r["respuesta"] = ("Modo demostración: la respuesta usa datos de ejemplo. Configurá IA_PROVEEDOR e "
                      "IA_API_KEY en el .env para que el modelo arme la consulta real.\n\n" + r["respuesta"])
    r.update(tipo="resultado", recortado=False, demo=True)
    return r
