from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.permissions import CondominioQuerysetMixin, EsDirectiva, TieneMembresia

from .models import Aviso
from .serializers import AvisoSerializer


class AvisoViewSet(CondominioQuerysetMixin, viewsets.ModelViewSet):
    queryset = Aviso.objects.select_related("autor__user")
    serializer_class = AvisoSerializer
    permission_classes = [IsAuthenticated, TieneMembresia]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_permissions(self):
        if self.request.method in ("POST", "DELETE"):
            return [IsAuthenticated(), EsDirectiva()]
        return super().get_permissions()

    def perform_create(self, serializer):
        membresia = self.request.user.membresia
        serializer.save(condominio=membresia.condominio, autor=membresia)
