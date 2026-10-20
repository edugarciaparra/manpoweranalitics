# Manpower Analytics

Portal de análisis en Django: una landing desde la que se entra a cada módulo
(Pedidos, Facturación, Clientes, Candidatos), cada uno con KPIs, gráfico, tabla
y un asistente de IA. **Todos los datos se leen de la base sgo_new**: no hay datos de ejemplo.

## Levantar en local (Windows / PyCharm)

```cmd
cd c:\projects\manpower_analytics
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

Abrís http://127.0.0.1:8000

## Estructura

```
manpower_analytics/
├── config/                 settings, urls raíz
├── apps/
│   ├── core/               landing, portada de cada módulo y pantalla de análisis
│   │   ├── analisis.py     catálogo de análisis y armado de secciones
│   │   ├── registry.py     descubre los módulos listados en settings
│   │   ├── graficos.py     estilo común de los gráficos ECharts
│   │   ├── estadistica.py  tendencia, estacionalidad y pronóstico
│   │   ├── db.py           acceso a sgo_new
│   │   └── utils.py        períodos, fechas, formatos ($, %, números)
│   ├── ia/                 asistente (proveedor intercambiable)
│   ├── pedidos/            ┐
│   ├── facturacion/        │ un módulo = una app:
│   ├── clientes/           │   modulo.py    título, ícono, color, resumen para la landing
│   ├── candidatos/         │   services.py  consultas a sgo_new
│   └── entrevistas/        ┘   analisis.py  los análisis del módulo, uno por función
├── templates/
│   ├── base.html
│   └── partials/menu_analisis.html   menú lateral del módulo
└── static/css, static/js
```

## Cómo es un análisis

Cada análisis es profundo: en una misma pantalla combina qué pasó, por qué, qué se
espera y qué conviene hacer. Arriba muestra 4 indicadores y las conclusiones; abajo,
varias secciones, cada una con su gráfico, su lectura y, si corresponde, tabla y
acciones recomendadas.

Para agregar uno, en el `analisis.py` del módulo:

```python
from apps.core.analisis import Catalogo, seccion

@catalogo.registrar("mi-analisis", "Título", "Descripción corta.", icono="bi-graph-up")
def mi_analisis(periodo):
    return {
        "kpis": [...],           # 4 indicadores
        "conclusiones": [...],   # lo más importante, en 3 o 4 frases
        "secciones": [
            seccion("Cómo evolucionó...", grafico={...}, lectura=[...]),
            seccion("Qué conviene hacer", acciones=[...], lectura=[...]),
        ],
        "sugerencias": [...],    # preguntas para el asistente
        "contexto_ia": {...},    # datos resumidos para el asistente
    }
```

Para que un gráfico abra el detalle de registros al hacer clic, la sección lleva
`detalle="clave"` y el módulo registra la función que arma la tabla:

```python
@catalogo.detalle("mi-analisis")
def detalle(clave, valor, serie, periodo):
    # valor = categoría cliqueada (barra, mes, departamento...), serie = nombre de la serie
    return {"titulo": "...", "columnas": [...], "filas": [[...], ...]}
```

El modal trae buscador, paginado y exportación a Excel (CSV). Muestra hasta 2.000 filas.

Aparece solo en el menú lateral y en la portada del módulo. Con `usa_periodo=False`
muestra la foto de hoy y no tiene selector de período.

## Agregar un módulo nuevo

1. Copiar una carpeta de módulo (por ejemplo `apps/clientes`) con otro nombre
2. Ajustar `modulo.py`, `services.py` y `analisis.py`
3. Agregar `"apps.nombre"` en `INSTALLED_APPS` y en `MODULOS_ANALISIS` (`config/settings.py`)

No hace falta tocar las URLs: `/nombre/` y `/nombre/<analisis>/` se resuelven solas.

## Base de Manpower (SQL Server)

Se configura en `.env` con las variables `SGO_DB_*` (servidor `EGARCIA-LATITUD`,
base `sgo_new`, autenticación de Windows si usuario y contraseña quedan vacíos).

Probar la conexión:

```cmd
python manage.py probar_sgo
```

- Las tablas internas de Django van a SQLite; en `sgo_new` no se crea ni se migra nada.
- Los módulos leen con `apps.core.db.consultar(sql, params)`, que devuelve una lista de dicts.
- Por defecto usa la misma conexión que el SGO: `EGARCIA-LATITUD` / `sgo_new` con autenticación de Windows y ODBC Driver 17. Si la base no responde, cada pantalla muestra el error.
- Las variables llevan prefijo `SGO_` para no chocar con un `DB_USER` definido en Windows,
  y el `.env` siempre le gana a las variables del sistema.

## Tablas de referencia

Las descripciones (motivos de baja, niveles educativos, cursos, idiomas,
departamentos, localidades, estados civiles) nunca se escriben en el código:
salen de sus tablas en `sgo_new` con JOIN, o desde `apps/core/catalogos.py`
(`catalogo("CausalesBaja")`, `cursos()`, ...).

Los datos se guardan 15 minutos en memoria (`apps/core/cache.py`) para no
consultar la base en cada pantalla.

## Asistente de IA

En `.env`: `IA_PROVEEDOR` (`anthropic`, `openai` y compatibles, `azure`, `gemini`),
`IA_API_KEY` y opcionalmente `IA_MODELO` / `IA_URL`. Se conecta por HTTP, sin instalar nada.

La IA nunca se conecta a la base. En «Preguntale a la base» arma el SQL, el portal
lo valida (solo lectura, tablas permitidas, sin datos personales) y lo ejecuta, y
la IA solo redacta la respuesta sobre esas filas. En el asistente de cada pantalla
recibe los números que esa pantalla ya leyó de la base.

## Pendiente

- Login (hoy el nombre del usuario está fijo en `apps/core/views.py`)
