from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, View

from core.mixins import CondominioFormMixin, CondominioRequiredMixin, SoloDirectivaMixin

from .forms import GastoComunForm
from .models import CuotaUnidad, GastoComun


class GastoComunListView(SoloDirectivaMixin, CondominioFormMixin, ListView):
    model = GastoComun
    template_name = "gastoscomunes/gasto_list.html"
    context_object_name = "gastos"


class GastoComunCreateView(SoloDirectivaMixin, CondominioFormMixin, CreateView):
    model = GastoComun
    form_class = GastoComunForm
    template_name = "gastoscomunes/gasto_form.html"
    success_url = reverse_lazy("gastos-comunes-list")

    def form_valid(self, form):
        if form.cleaned_data["modo"] == "por_unidad":
            num_unidades = self.condominio.unidades.count()
            form.instance.monto_total = form.cleaned_data["monto_por_unidad"] * num_unidades
        else:
            form.instance.monto_por_unidad = None
        response = super().form_valid(form)
        self.object.generar_cuotas()
        return response


class CuotaListView(SoloDirectivaMixin, CondominioRequiredMixin, ListView):
    template_name = "gastoscomunes/cuota_list.html"
    context_object_name = "cuotas"

    def get_queryset(self):
        return CuotaUnidad.objects.filter(gasto_comun__condominio=self.condominio, gasto_comun_id=self.kwargs["gasto_pk"]).select_related("unidad")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gasto"] = get_object_or_404(GastoComun, pk=self.kwargs["gasto_pk"], condominio=self.condominio)
        return context


class MarcarCuotaPagadaView(SoloDirectivaMixin, CondominioRequiredMixin, View):
    def post(self, request, pk):
        cuota = get_object_or_404(CuotaUnidad, pk=pk, gasto_comun__condominio=self.condominio)
        cuota.estado = "pagado"
        cuota.fecha_pago = timezone.localdate()
        cuota.save()
        return redirect("gastos-comunes-cuotas", gasto_pk=cuota.gasto_comun_id)


class MisCuotasView(CondominioRequiredMixin, ListView):
    """Vista del residente para sus propias cuotas -- antes solo existía por API (pensada para la futura app móvil)."""

    template_name = "gastoscomunes/mis_cuotas.html"
    context_object_name = "cuotas"

    def get_queryset(self):
        if self.membresia.unidad_id is None:
            return CuotaUnidad.objects.none()
        return CuotaUnidad.objects.filter(unidad=self.membresia.unidad).select_related("gasto_comun").order_by("-gasto_comun__fecha_emision")
