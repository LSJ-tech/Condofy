from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import DispositivoPush, SuscripcionWebPush
from .serializers import DispositivoPushSerializer, SuscripcionWebPushSerializer


class DispositivoPushCreateView(generics.CreateAPIView):
    """Registra (o actualiza) el token de push del dispositivo actual.

    Un mismo token puede reasignarse de usuario si alguien cierra sesión y
    otra persona inicia sesión en el mismo teléfono -- por eso es
    update_or_create por token, no un create simple.
    """

    serializer_class = DispositivoPushSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        dispositivo, _ = DispositivoPush.objects.update_or_create(
            token=serializer.validated_data["token"],
            defaults={"user": self.request.user, "plataforma": serializer.validated_data["plataforma"]},
        )
        serializer.instance = dispositivo


class SuscripcionWebPushCreateView(generics.CreateAPIView):
    """Registra (o actualiza) la suscripción de Web Push del navegador
    actual (la PWA) -- mismo criterio que DispositivoPush: update_or_create
    por endpoint, por si el navegador reasigna la suscripción a otra
    cuenta en el mismo equipo."""

    serializer_class = SuscripcionWebPushSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        suscripcion, _ = SuscripcionWebPush.objects.update_or_create(
            endpoint=serializer.validated_data["endpoint"],
            defaults={
                "user": self.request.user,
                "p256dh": serializer.validated_data["p256dh"],
                "auth": serializer.validated_data["auth"],
            },
        )
        serializer.instance = suscripcion
