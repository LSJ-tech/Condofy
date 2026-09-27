from rest_framework import serializers

from .models import Aviso


class AvisoSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.CharField(source="autor.user.get_full_name", read_only=True)

    class Meta:
        model = Aviso
        fields = ["id", "titulo", "cuerpo", "fecha_creacion", "autor_nombre"]
