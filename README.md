# Manpower Analytics

Portal de análisis en Django: una landing desde la que se entra a cada módulo
(Pedidos, Facturación, Clientes, Candidatos), cada uno con KPIs, gráfico, tabla
y un asistente de IA. **Por ahora los datos son de ejemplo, fijos en el código.**

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
│   │   ├── datos_ejemplo.py procesos de selección de ejemplo (Candidatos y Entrevistas)
│   │   ├── db.py           acceso a sgo_new
│   │   └── utils.py        períodos, fechas, formatos ($, %, números)
│   ├── ia/                 asistente (proveedor intercambiable)
│   ├── pedidos/            ┐
│   ├── facturacion/        │ un módulo = una app:
│   ├── clientes/           │   modulo.py    título, ícono, color, resumen para la landing
│   ├── candidatos/         │   services.py  datos (hoy de ejemplo, después sgo_new)
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
- Si `SGO_DB_HOST` queda vacío, el proyecto sigue andando con los datos de ejemplo.
- Las variables llevan prefijo `SGO_` para no chocar con un `DB_USER` definido en Windows,
  y el `.env` siempre le gana a las variables del sistema.

## Asistente de IA

En `.env`, `IA_PROVEEDOR=mock` responde textos de ejemplo sin clave.
Para usar un modelo real, cambiá a `claude`, `openai`, `azure` o `gemini`,
completá `IA_API_KEY` e `IA_MODELO` e instalá el SDK correspondiente
(está comentado en `requirements.txt`). No hay que tocar código.

## Pendiente

- Pasar cada módulo de datos de ejemplo a consultas reales en `sgo_new`
- Login (hoy el nombre del usuario está fijo en `apps/core/views.py`)
- Conectar el asistente a un proveedor real
