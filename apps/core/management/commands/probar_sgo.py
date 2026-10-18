"""
Prueba la conexión a la base de Manpower.

    python manage.py probar_sgo
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.db import consultar, sgo_configurada


class Command(BaseCommand):
    help = "Prueba la conexión a la base de Manpower (alias sgo)."

    def handle(self, *args, **options):
        if not sgo_configurada():
            raise CommandError("SGO_DB_HOST está vacío en el .env. Completalo y probá de nuevo.")

        cfg = settings.DATABASES["sgo"]
        auth = f"usuario {cfg['USER']}" if cfg["USER"] else "autenticación de Windows"
        self.stdout.write(f"Conectando a {cfg['HOST']} / {cfg['NAME']} con {auth}...")

        try:
            fila = consultar(
                "SELECT @@SERVERNAME AS Servidor, DB_NAME() AS Base, SUSER_SNAME() AS Usuario, "
                "(SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES) AS Tablas"
            )[0]
        except Exception as e:  # noqa: BLE001
            raise CommandError(f"No se pudo conectar: {e}")

        self.stdout.write(self.style.SUCCESS("Conectado"))
        for clave, valor in fila.items():
            self.stdout.write(f"  {clave}: {valor}")
