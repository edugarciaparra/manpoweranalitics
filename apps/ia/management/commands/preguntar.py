"""python manage.py preguntar "¿Cuántos pedidos hubo este año por división?"

Prueba la consulta en lenguaje natural desde la consola: muestra el SQL, las
primeras filas y la respuesta.
"""
from django.core.management.base import BaseCommand

from apps.ia.consulta import ErrorConsulta, responder_pregunta


class Command(BaseCommand):
    help = "Hace una pregunta en lenguaje natural a la base de Manpower."

    def add_arguments(self, parser):
        parser.add_argument("pregunta")

    def handle(self, *args, pregunta, **opciones):
        try:
            r = responder_pregunta(pregunta)
        except ErrorConsulta as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return
        if r.get("sql"):
            self.stdout.write(self.style.MIGRATE_HEADING("SQL"))
            self.stdout.write(r["sql"])
        if r.get("columnas"):
            self.stdout.write(self.style.MIGRATE_HEADING(f"Resultado ({len(r['filas'])} filas)"))
            self.stdout.write(" | ".join(r["columnas"]))
            for f in r["filas"][:15]:
                self.stdout.write(" | ".join("" if v is None else str(v) for v in f))
        self.stdout.write(self.style.MIGRATE_HEADING("Respuesta"))
        self.stdout.write(r.get("respuesta", ""))
