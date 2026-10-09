from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView
from django.views.generic.base import View

from core.mixins import CondominioFormMixin, CondominioRequiredMixin, EsDirectivaOAdministracionMixin, SoloAdministracionMixin

from .calculo import calcular_liquidacion
from .forms import EmpleadoForm
from .liquidacion_pdf import enviar_liquidacion_por_correo, generar_liquidacion_pdf
from .models import Empleado, Liquidacion, ParametrosPeriodo, TramoImpuestoUnico


class EmpleadoListView(EsDirectivaOAdministracionMixin, CondominioFormMixin, ListView):
    model = Empleado
    template_name = "personal/empleado_list.html"
    context_object_name = "empleados"

    def get_queryset(self):
        return super().get_queryset().order_by("-activo", "nombre")


class EmpleadoCreateView(SoloAdministracionMixin, CondominioFormMixin, CreateView):
    model = Empleado
    form_class = EmpleadoForm
    template_name = "personal/empleado_form.html"
    success_url = reverse_lazy("empleados")


class EmpleadoUpdateView(SoloAdministracionMixin, CondominioFormMixin, UpdateView):
    model = Empleado
    form_class = EmpleadoForm
    template_name = "personal/empleado_form.html"
    success_url = reverse_lazy("empleados")


class LiquidacionListView(EsDirectivaOAdministracionMixin, CondominioRequiredMixin, ListView):
    template_name = "personal/liquidacion_list.html"
    context_object_name = "liquidaciones"

    def get_queryset(self):
        self.empleado = get_object_or_404(Empleado, pk=self.kwargs["empleado_pk"], condominio=self.condominio)
        return Liquidacion.objects.filter(empleado=self.empleado)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["empleado"] = self.empleado
        return context


class LiquidacionGenerarView(SoloAdministracionMixin, CondominioRequiredMixin, View):
    def post(self, request, empleado_pk):
        empleado = get_object_or_404(Empleado, pk=empleado_pk, condominio=self.condominio)
        periodo = request.POST.get("periodo", "").strip()
        if not periodo:
            messages.error(request, "Elige el periodo.")
            return redirect("liquidaciones", empleado_pk=empleado.pk)

        if Liquidacion.objects.filter(empleado=empleado, periodo=periodo).exists():
            messages.error(request, f"Ya existe una liquidación de {empleado.nombre} para {periodo}.")
            return redirect("liquidaciones", empleado_pk=empleado.pk)

        try:
            parametros = ParametrosPeriodo.objects.get(periodo=periodo)
        except ParametrosPeriodo.DoesNotExist:
            messages.error(
                request,
                f"Faltan los parámetros legales de {periodo}. Configúralos en /admin/personal/parametrosperiodo/ antes de generar liquidaciones de ese mes.",
            )
            return redirect("liquidaciones", empleado_pk=empleado.pk)

        tramos = list(TramoImpuestoUnico.objects.all())
        datos = calcular_liquidacion(empleado, parametros, tramos)
        liquidacion = Liquidacion.objects.create(empleado=empleado, periodo=periodo, **datos)

        correo_destino = request.POST.get("correo_destino", "").strip()
        if correo_destino:
            enviar_liquidacion_por_correo(liquidacion, correo_destino)

        messages.success(request, f"Liquidación de {empleado.nombre} para {periodo} generada.")
        return redirect("liquidaciones", empleado_pk=empleado.pk)


class LiquidacionPDFView(SoloAdministracionMixin, CondominioRequiredMixin, View):
    def get(self, request, pk):
        liquidacion = get_object_or_404(
            Liquidacion.objects.select_related("empleado", "empleado__condominio"),
            pk=pk, empleado__condominio=self.condominio,
        )
        return generar_liquidacion_pdf(liquidacion)
