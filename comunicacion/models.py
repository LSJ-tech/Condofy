from django.db import models

from core.models import Condominio, Membresia


class Aviso(models.Model):
    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="avisos")
    autor = models.ForeignKey(Membresia, on_delete=models.CASCADE, related_name="avisos")
    titulo = models.CharField(max_length=150)
    cuerpo = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.titulo
