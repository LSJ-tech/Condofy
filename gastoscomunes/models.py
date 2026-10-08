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
    monto_total = models.PositiveIntegerField(help_text="En pesos chilenos -- sin centavos.")
    monto_por_unidad = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Si el cargo es una cuota fija por unidad (no prorrateada por alícuota), queda el valor acá y en monto_total queda el total resultante.",
    )
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    es_voluntario = models.BooleanField(
        default=False,
        help_text="Aporte voluntario (ej. recaudar para un proyecto puntual) -- cada unidad dona lo que quiera, no genera morosidad ni monto obligatorio.",
    )

    class Meta:
        ordering = ["-fecha_emision"]
        constraints = [
            models.UniqueConstraint(fields=["condominio", "periodo"], name="gastocomun_periodo_unico_por_condominio"),
        ]

    def __str__(self):
        return f"{self.condominio} - {self.periodo}"

    def generar_cuotas(self):
        """Si `monto_por_unidad` está definido, cada unidad paga exactamente ese
        valor fijo (sin importar alícuota). Si no, prorratea `monto_total` entre
        las unidades según su alícuota (si está definida, >0) o en partes
        iguales si ninguna la tiene. No pisa cuotas ya generadas para este gasto."""
        unidades = list(self.condominio.unidades.all())
        if not unidades or self.cuotas.exists():
            return
        cuotas = []
        if self.es_voluntario:
            for unidad in unidades:
                cuotas.append(CuotaUnidad(gasto_comun=self, unidad=unidad, monto=0))
        elif self.monto_por_unidad is not None:
            for unidad in unidades:
                cuotas.append(CuotaUnidad(gasto_comun=self, unidad=unidad, monto=self.monto_por_unidad))
        else:
            suma_alicuotas = sum((u.alicuota for u in unidades), Decimal("0"))
            for unidad in unidades:
                if suma_alicuotas > 0:
                    monto = round(self.monto_total * unidad.alicuota / suma_alicuotas)
                else:
                    monto = round(self.monto_total / len(unidades))
                cuotas.append(CuotaUnidad(gasto_comun=self, unidad=unidad, monto=monto))
        CuotaUnidad.objects.bulk_create(cuotas)


class CuotaUnidad(models.Model):
    gasto_comun = models.ForeignKey(GastoComun, on_delete=models.CASCADE, related_name="cuotas")
    unidad = models.ForeignKey(Unidad, on_delete=models.CASCADE, related_name="cuotas")
    monto = models.PositiveIntegerField(help_text="En pesos chilenos -- sin centavos.")
    estado = models.CharField(max_length=10, choices=ESTADO_CUOTA_CHOICES, default="pendiente")
    fecha_pago = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["unidad__numero"]
        constraints = [
            models.UniqueConstraint(fields=["gasto_comun", "unidad"], name="cuota_unica_por_gasto_y_unidad"),
        ]

    def __str__(self):
        return f"{self.unidad} - {self.gasto_comun.periodo}: {self.get_estado_display()}"
