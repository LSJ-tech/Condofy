import calendar
from datetime import date

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.db.models.functions import Length
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, View

from core.mixins import CondominioFormMixin, CondominioRequiredMixin, EsDirectivaOAdministracionMixin
from core.models import Torre

from .forms import GastoComunForm
from .models import CuotaUnidad, GastoComun


class GastoComunListView(EsDirectivaOAdministracionMixin, CondominioFormMixin, ListView):
    model = GastoComun
    template_name = "gastoscomunes/gasto_list.html"
    context_object_name = "gastos"


class GastoComunCreateView(EsDirectivaOAdministracionMixin, CondominioFormMixin, CreateView):
    model = GastoComun
    form_class = GastoComunForm
    template_name = "gastoscomunes/gasto_form.html"
    success_url = reverse_lazy("gastos-comunes-list")

    def form_valid(self, form):
        modo = form.cleaned_data["modo"]
        form.instance.es_voluntario = modo == "donacion"
        if modo == "por_unidad":
            num_unidades = self.condominio.unidades.count()
            form.instance.monto_total = form.cleaned_data["monto_por_unidad"] * num_unidades
        elif modo == "donacion":
            form.instance.monto_por_unidad = None
            form.instance.monto_total = form.cleaned_data.get("monto_total") or 0
        else:
            form.instance.monto_por_unidad = None

        anio, mes = map(int, form.cleaned_data["periodo"].split("-"))
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        form.instance.fecha_vencimiento = date(anio, mes, ultimo_dia)

        response = super().form_valid(form)
        self.object.generar_cuotas()
        return response


class CuotaListView(EsDirectivaOAdministracionMixin, CondominioRequiredMixin, ListView):
    template_name = "gastoscomunes/cuota_list.html"
    context_object_name = "cuotas"
    paginate_by = 50

    def get_queryset(self):
        qs = CuotaUnidad.objects.filter(
            gasto_comun__condominio=self.condominio, gasto_comun_id=self.kwargs["gasto_pk"]
        ).select_related("unidad", "unidad__torre")
        torre_id = self.request.GET.get("torre")
        if torre_id:
            qs = qs.filter(unidad__torre_id=torre_id)
        return qs.annotate(_torre_len=Length("unidad__torre__nombre")).order_by("_torre_len", "unidad__torre__nombre", "unidad__numero")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gasto = get_object_or_404(GastoComun, pk=self.kwargs["gasto_pk"], condominio=self.condominio)
        context["gasto"] = gasto
        context["gastos"] = GastoComun.objects.filter(condominio=self.condominio).order_by("-periodo")
        context["torres"] = Torre.objects.filter(condominio=self.condominio).annotate(_len=Length("nombre")).order_by("_len", "nombre")
        context["torre_seleccionada"] = self.request.GET.get("torre", "")
        if gasto.es_voluntario:
            agregados = CuotaUnidad.objects.filter(gasto_comun=gasto).aggregate(
                recaudado=Sum("monto", filter=Q(estado="pagado")),
                pagadas=Count("id", filter=Q(estado="pagado")),
                total=Count("id"),
            )
            context["recaudado"] = agregados["recaudado"] or 0
            context["cuotas_pagadas_count"] = agregados["pagadas"]
            context["cuotas_total_count"] = agregados["total"]
        return context


class MarcarCuotaPagadaView(EsDirectivaOAdministracionMixin, CondominioRequiredMixin, View):
    def post(self, request, pk):
        cuota = get_object_or_404(CuotaUnidad, pk=pk, gasto_comun__condominio=self.condominio)
        if cuota.gasto_comun.es_voluntario:
            try:
                monto = int(request.POST.get("monto", ""))
            except (TypeError, ValueError):
                monto = 0
            if monto <= 0:
                messages.error(request, "Ingresa un monto válido para registrar el aporte.")
                return redirect("gastos-comunes-cuotas", gasto_pk=cuota.gasto_comun_id)
            cuota.monto = monto
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
