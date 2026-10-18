from django.db import models


class ConsultaIA(models.Model):
    """Registro de cada pregunta en lenguaje natural: qué se preguntó, qué SQL se ejecutó y cómo terminó."""
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.CharField(max_length=150, blank=True)
    pregunta = models.TextField()
    sql = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, blank=True)  # resultado, aclaracion, sin_base, error
    filas = models.PositiveIntegerField(default=0)
    segundos = models.FloatField(default=0)
    error = models.TextField(blank=True)
    proveedor = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "consulta en lenguaje natural"
        verbose_name_plural = "consultas en lenguaje natural"

    def __str__(self):
        return self.pregunta[:80]
