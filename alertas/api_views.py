from datetime import timedelta

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import CondominioQuerysetMixin, TieneMembresia

from .models import MINUTOS_AUTO_CIERRE, Alerta
from .serializers import AlertaSerializer
from .services import notificar_alerta


class AlertaViewSet(CondominioQuerysetMixin, viewsets.ModelViewSet):
    queryset = Alerta.objects.select_related("autor__user", "autor__unidad", "resuelta_por__user", "resuelta_por__unidad")
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticated, TieneMembresia]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        condominio_id = self.request.user.membresia.condominio_id
        limite = timezone.now() - timedelta(minutes=MINUTOS_AUTO_CIERRE)
        Alerta.objects.filter(condominio_id=condominio_id, estado="activa", fecha_creacion__lt=limite).update(estado="auto_cerrada")

        qs = super().get_queryset()
        estado = self.request.query_params.get("estado")
        if estado == "recientes":
            hace_24h = timezone.now() - timedelta(hours=24)
            qs = qs.exclude(estado="activa").filter(fecha_creacion__gte=hace_24h)[:5]
        elif estado:
            qs = qs.filter(estado=estado)
        return qs

    def perform_create(self, serializer):
        membresia = self.request.user.membresia
        alerta = serializer.save(condominio=membresia.condominio, autor=membresia)
        notificar_alerta(alerta)

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated, TieneMembresia])
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
