from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Condominio, Membresia, Unidad


class CondominioResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condominio
        fields = ["id", "nombre", "plan", "puede_operar"]


class UnidadResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidad
        fields = ["id", "numero"]


class MembresiaSerializer(serializers.ModelSerializer):
    condominio = CondominioResumenSerializer(read_only=True)
    unidad = UnidadResumenSerializer(read_only=True)
    nombre = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = Membresia
        fields = ["rol", "condominio", "unidad", "nombre"]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Igual al login estándar de simplejwt, pero además devuelve la membresía
    del usuario en el mismo response -- evita que la app tenga que hacer un
    segundo request a /auth/me/ apenas inicia sesión."""

    def validate(self, attrs):
        data = super().validate(attrs)
        membresia = getattr(self.user, "membresia", None)
        data["membresia"] = MembresiaSerializer(membresia).data if membresia else None
        return data
