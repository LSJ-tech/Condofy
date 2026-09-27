from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import DispositivoPush
from .serializers import DispositivoPushSerializer


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
