from django.views.generic import ListView

from core.mixins import CondominioRequiredMixin

from .models import Alerta


class AlertaHistorialView(CondominioRequiredMixin, ListView):
    """Historial completo de alertas del condominio -- abierto a cualquier rol,
    igual que resolver/ver el mapa (ver EsDirectivaOAdministracionMixin para lo
    que sí sigue restringido por rol)."""

    template_name = "alertas/alerta_historial.html"
    context_object_name = "alertas"
    paginate_by = 20

    def get_queryset(self):
        qs = Alerta.objects.filter(condominio=self.condominio).select_related("autor__user", "autor__unidad", "resuelta_por__user", "resuelta_por__unidad")
        estado = self.request.GET.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estado_seleccionado"] = self.request.GET.get("estado", "")
        return context
