"""
Configuración del proyecto Manpower Analytics.

Los valores sensibles y los que cambian por empresa (clave de IA, proveedor,
base de datos) se leen del archivo .env. Ver .env.example.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv es opcional
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent


def _cargar_env(ruta):
    """Carga el .env aunque se haya guardado como UTF-16 o UTF-8 con BOM
    (pasa al guardarlo desde el Bloc de notas o PowerShell).
    override=True: los valores del .env le ganan a las variables de Windows."""
    if not load_dotenv or not ruta.exists():
        return
    crudo = ruta.read_bytes()
    for codificacion in ("utf-8-sig", "utf-16"):
        try:
            texto = crudo.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise RuntimeError(f"No se pudo leer {ruta}: guardalo como UTF-8.")
    from io import StringIO
    load_dotenv(stream=StringIO(texto), override=True)


_cargar_env(BASE_DIR / ".env")


def env(nombre, defecto=None):
    return os.environ.get(nombre, defecto)


def env_bool(nombre, defecto=False):
    return str(env(nombre, defecto)).lower() in ("1", "true", "si", "sí", "yes")


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-solo-local-cambiar-en-produccion")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps del proyecto
    "apps.core",
    "apps.ia",
    "apps.pedidos",
    "apps.facturacion",
    "apps.clientes",
    "apps.candidatos",
    "apps.entrevistas",
    "apps.candidatosweb",
]

# Módulos de análisis que aparecen en la landing, en este orden.
# Para agregar uno nuevo: crear la app con su modulo.py y sumarla acá.
MODULOS_ANALISIS = [
    "apps.pedidos",
    "apps.facturacion",
    "apps.clientes",
    "apps.candidatosweb",
    # "apps.candidatos",  # fuera del menú por ahora
    "apps.entrevistas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.modulos",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# "default": SQLite, solo para las tablas internas de Django (sesiones, admin),
#            así no se crea nada en la base de Manpower.
# "sgo":     SQL Server de Manpower, solo para leer datos en los módulos.
#            Si SGO_DB_HOST está vacío no se configura y los módulos usan
#            los datos de ejemplo.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

SGO_DB_HOST = env("SGO_DB_HOST", "")
if SGO_DB_HOST:
    DATABASES["sgo"] = {
        "ENGINE": "mssql",
        "NAME": env("SGO_DB_NAME", "sgo_new"),
        "HOST": SGO_DB_HOST,
        "PORT": env("SGO_DB_PORT", ""),
        # Usuario vacío = autenticación de Windows (Trusted Connection)
        "USER": env("SGO_DB_USER", ""),
        "PASSWORD": env("SGO_DB_PASSWORD", ""),
        "OPTIONS": {"driver": env("SGO_DB_DRIVER", "ODBC Driver 17 for SQL Server")},
    }

# Evita que Django intente crear sus tablas en la base de Manpower
DATABASE_ROUTERS = ["apps.core.db.SoloLecturaSgoRouter"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-uy"
TIME_ZONE = "America/Montevideo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Asistente de IA -------------------------------------------------------
# Se conecta por HTTP a la API que se configure (ver apps/ia/proveedores.py).
# IA_PROVEEDOR: mock | anthropic | openai (y compatibles) | azure | gemini
# Con "mock" responde con datos de ejemplo y no necesita clave.
IA_PROVEEDOR = env("IA_PROVEEDOR", "mock")
IA_API_KEY = env("IA_API_KEY", "")
IA_MODELO = env("IA_MODELO", "")
IA_URL = env("IA_URL", "")
IA_AZURE_ENDPOINT = env("IA_AZURE_ENDPOINT", "")  # nombre anterior de IA_URL para Azure
IA_AZURE_VERSION = env("IA_AZURE_VERSION", "2024-10-21")
