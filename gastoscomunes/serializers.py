from rest_framework import serializers

from .models import CuotaUnidad


class CuotaUnidadSerializer(serializers.ModelSerializer):
    periodo = serializers.CharField(source="gasto_comun.periodo", read_only=True)
    fecha_vencimiento = serializers.DateField(source="gasto_comun.fecha_vencimiento", read_only=True)
    unidad_numero = serializers.CharField(source="unidad.numero", read_only=True)

    class Meta:
        model = CuotaUnidad
        fields = ["id", "periodo", "monto", "estado", "fecha_pago", "fecha_vencimiento", "unidad_numero"]
