from decimal import Decimal

from django.db import models

from core.models import Condominio, Unidad

ESTADO_CUOTA_CHOICES = [
    ("pendiente", "Pendiente"),
    ("pagado", "Pagado"),
    ("vencido", "Vencido"),
]


class GastoComun(models.Model):
    """El cargo mensual general del condominio, antes de prorratear por unidad."""

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="gastos_comunes")
    periodo = models.CharField(max_length=20, help_text="Ej. '2026-09'.")
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField()

    class Meta:
        ordering = ["-fecha_emision"]
        constraints = [
            models.UniqueConstraint(fields=["condominio", "periodo"], name="gastocomun_periodo_unico_por_condominio"),
        ]

    def __str__(self):
        return f"{self.condominio} - {self.periodo}"

    def generar_cuotas(self):
        """Prorratea `monto_total` entre las unidades del condominio, según su
        alícuota si está definida (>0), o en partes iguales si ninguna la tiene.
        No pisa cuotas ya generadas para este gasto."""
        unidades = list(self.condominio.unidades.all())
        if not unidades or self.cuotas.exists():
            return
        suma_alicuotas = sum((u.alicuota for u in unidades), Decimal("0"))
        cuotas = []
        for unidad in unidades:
            if suma_alicuotas > 0:
                monto = (self.monto_total * unidad.alicuota / suma_alicuotas).quantize(Decimal("0.01"))
            else:
                monto = (self.monto_total / len(unidades)).quantize(Decimal("0.01"))
            cuotas.append(CuotaUnidad(gasto_comun=self, unidad=unidad, monto=monto))
        CuotaUnidad.objects.bulk_create(cuotas)


class CuotaUnidad(models.Model):
    gasto_comun = models.ForeignKey(GastoComun, on_delete=models.CASCADE, related_name="cuotas")
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name="cuotas")
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=10, choices=ESTADO_CUOTA_CHOICES, default="pendiente")
    fecha_pago = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["unidad__numero"]
        constraints = [
            models.UniqueConstraint(fields=["gasto_comun", "unidad"], name="cuota_unica_por_gasto_y_unidad"),
        ]

    def __str__(self):
        return f"{self.unidad} - {self.gasto_comun.periodo}: {self.get_estado_display()}"
