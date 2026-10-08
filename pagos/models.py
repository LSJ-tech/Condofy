from django.db import models

from core.models import PLAN_CHOICES, Condominio, Membresia

ESTADO_PAGO_CHOICES = [
    ("pendiente", "Pendiente"),
    ("aprobado", "Aprobado"),
    ("rechazado", "Rechazado"),
]

TIPO_PAGO_CHOICES = [
    ("suscripcion", "Suscripción"),
    ("donacion", "Donación"),
]


class Pago(models.Model):
    """Pago de la suscripción SaaS (condominio -> DevQuad), o una donación
    voluntaria de un condominio para apoyar el desarrollo de la plataforma
    (ver `tipo`) -- ninguna de las dos se debe confundir con los pagos de
    gastos comunes (residente -> su propio condominio, ver la app
    `gastoscomunes`, un flujo de dinero de terceros con mecanismo distinto)."""

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="pagos")
    membresia = models.ForeignKey(
        Membresia, on_delete=models.SET_NULL, null=True, blank=True, related_name="donaciones",
        help_text="Quién donó (torre/unidad incluida) -- vacío en pagos de suscripción, que son del condominio como tal.",
    )
    tipo = models.CharField(max_length=15, choices=TIPO_PAGO_CHOICES, default="suscripcion")
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, blank=True, help_text="Vacío si es una donación -- no está ligada a ningún plan.")
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
