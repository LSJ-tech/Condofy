from django.db import models

from core.models import PLAN_CHOICES, Condominio

ESTADO_PAGO_CHOICES = [
    ("pendiente", "Pendiente"),
    ("aprobado", "Aprobado"),
    ("rechazado", "Rechazado"),
]


class Pago(models.Model):
    """Pago de la suscripción SaaS (condominio -> DevQuad). No confundir con
    los pagos de gastos comunes (residente -> su propio condominio, ver
    la app `gastoscomunes` -- ese flujo de dinero es de terceros y usa un
    mecanismo distinto, ver el plan del proyecto)."""

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="pagos")
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=10, choices=ESTADO_PAGO_CHOICES, default="pendiente")
    mercadopago_preference_id = models.CharField(max_length=100, blank=True)
    mercadopago_payment_id = models.CharField(max_length=100, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Pago #{self.pk} - {self.condominio} - {self.estado}"
