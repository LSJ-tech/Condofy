from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, View
from django.shortcuts import get_object_or_404, redirect

from core.mixins import CondominioRequiredMixin, SoloDirectivaOConserjeMixin

from .forms import RegistroIngresoForm
from .models import RegistroIngreso


class RegistroIngresoListView(SoloDirectivaOConserjeMixin, CondominioRequiredMixin, ListView):
    template_name = "accesos/registro_list.html"
    context_object_name = "registros"

    def get_queryset(self):
        return RegistroIngreso.objects.filter(unidad__condominio=self.condominio).select_related("unidad", "unidad__torre", "registrado_por")


class RegistroIngresoCreateView(SoloDirectivaOConserjeMixin, CondominioRequiredMixin, CreateView):
    model = RegistroIngreso
    form_class = RegistroIngresoForm
    template_name = "accesos/registro_form.html"
    success_url = reverse_lazy("registro-ingreso-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.condominio
        return kwargs

    def form_valid(self, form):
        form.instance.registrado_por = self.membresia
        return super().form_valid(form)


class RegistrarSalidaView(SoloDirectivaOConserjeMixin, CondominioRequiredMixin, View):
    def post(self, request, pk):
        registro = get_object_or_404(RegistroIngreso, pk=pk, unidad__condominio=self.condominio)
        registro.fecha_salida = timezone.now()
        registro.save()
        return redirect("registro-ingreso-list")
