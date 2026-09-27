from django.db import models

from core.models import Membresia, Unidad

MOTIVO_CHOICES = [
    ("visita", "Visita"),
    ("delivery", "Delivery"),
    ("proveedor", "Proveedor/servicio"),
    ("otro", "Otro"),
]


class RegistroIngreso(models.Model):
    """Registro manual de conserjería de quién entra al condominio.

    Fase 1: se tipea a mano desde el panel web. El modelo `Visita` (pre-registro
    del residente + QR para autoservicio) queda para Fase 2 -- no se crea
    todavía para no dejar un modelo sin flujo que lo use.
    """

    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name="registros_ingreso")
    registrado_por = models.ForeignKey(Membresia, on_delete=models.SET_NULL, null=True, related_name="registros_hechos")
    nombre_visitante = models.CharField(max_length=150)
    motivo = models.CharField(max_length=10, choices=MOTIVO_CHOICES, default="visita")
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    fecha_salida = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_ingreso"]

    def __str__(self):
        return f"{self.nombre_visitante} -> {self.unidad} ({self.fecha_ingreso:%Y-%m-%d %H:%M})"
