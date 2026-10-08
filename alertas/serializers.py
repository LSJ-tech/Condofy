from rest_framework import serializers

from .models import Alerta


class AlertaSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.CharField(source="autor.user.get_full_name", read_only=True)
    autor_unidad = serializers.CharField(source="autor.unidad.numero", read_only=True, default=None)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = Alerta
        fields = [
            "id", "tipo", "tipo_display", "estado", "mensaje", "latitud", "longitud",
            "fecha_creacion", "autor_nombre", "autor_unidad", "resuelta_por", "fecha_resolucion",
        ]
        read_only_fields = ["estado", "resuelta_por", "fecha_resolucion"]
