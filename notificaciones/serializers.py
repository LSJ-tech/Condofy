from rest_framework import serializers

from .models import DispositivoPush, SuscripcionWebPush


class DispositivoPushSerializer(serializers.ModelSerializer):
    # Sin esto, DRF agrega un UniqueValidator automático por el unique=True
    # del modelo -- rechazaría con 400 reenviar el mismo token en vez de
    # dejar que la vista haga el update_or_create (ver el docstring de
    # DispositivoPushCreateView: reenviar el mismo token es el caso normal).
    token = serializers.CharField(max_length=255, validators=[])

    class Meta:
        model = DispositivoPush
        fields = ["id", "token", "plataforma"]


class SuscripcionWebPushSerializer(serializers.ModelSerializer):
    endpoint = serializers.URLField(max_length=500, validators=[])

    class Meta:
        model = SuscripcionWebPush
        fields = ["id", "endpoint", "p256dh", "auth"]
