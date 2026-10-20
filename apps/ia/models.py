from django.db import models


class ConsultaIA(models.Model):
    """Cada pregunta a Rafa: qué se preguntó, qué SQL se ejecutó, cómo terminó y la respuesta que se mostró."""
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.CharField(max_length=150, blank=True)
    pregunta = models.TextField()
    sql = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, blank=True)  # resultado, aclaracion, sin_base, error
    filas = models.PositiveIntegerField(default=0)
    segundos = models.FloatField(default=0)
    error = models.TextField(blank=True)
    proveedor = models.CharField(max_length=20, blank=True)
    # Para conservar las conversaciones: de qué navegador (sesión), desde qué módulo y en qué conversación
    sesion = models.CharField(max_length=40, blank=True, db_index=True)
    modulo = models.CharField(max_length=30, blank=True)
    conversacion = models.CharField(max_length=36, blank=True, db_index=True)
    resultado = models.TextField(blank=True)  # JSON de la respuesta que se mostró (sin el SQL)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "consulta en lenguaje natural"
        verbose_name_plural = "consultas en lenguaje natural"

    def __str__(self):
        return self.pregunta[:80]
