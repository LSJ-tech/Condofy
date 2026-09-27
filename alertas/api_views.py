from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import CondominioQuerysetMixin, EsDirectivaOConserje, TieneMembresia

from .models import Alerta
from .serializers import AlertaSerializer
from .services import notificar_alerta


class AlertaViewSet(CondominioQuerysetMixin, viewsets.ModelViewSet):
    queryset = Alerta.objects.select_related("autor__user", "autor__unidad")
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticated, TieneMembresia]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        membresia = self.request.user.membresia
        alerta = serializer.save(condominio=membresia.condominio, autor=membresia)
        notificar_alerta(alerta)

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated, EsDirectivaOConserje])
    def resolver(self, request, pk=None):
        alerta = self.get_object()
        estado = request.data.get("estado", "resuelta")
        if estado not in ("resuelta", "falsa_alarma"):
            return Response({"detail": "estado inválido."}, status=400)
        alerta.estado = estado
        alerta.resuelta_por = request.user.membresia
        alerta.fecha_resolucion = timezone.now()
        alerta.save()
        return Response(AlertaSerializer(alerta).data)
