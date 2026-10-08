import datetime
import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from .mercadopago_client import crear_preferencia_pago, obtener_pago_mercadopago
from .models import Pago


class IniciarPagoView(LoginRequiredMixin, View):
    """A propósito NO usa CondominioRequiredMixin: esta vista es justo para
    cuando el condominio está vencido, y ese mixin lo mandaría a
    suscripcion-vencida antes de dejarlo pagar."""

    def post(self, request, *args, **kwargs):
        membresia = getattr(request.user, "membresia", None)
        if membresia is None:
            messages.error(request, "Tu cuenta no está vinculada a ningún condominio.")
            return redirect("login")

        condominio = membresia.condominio
        destino = "inicio" if condominio.puede_operar else "suscripcion-vencida"

        if membresia.rol != "directiva":
            messages.error(request, "Solo la directiva puede gestionar el pago de la suscripción.")
            return redirect(destino)

        if not settings.MERCADOPAGO_ACCESS_TOKEN:
            messages.error(request, "El pago en línea todavía no está disponible. Escríbenos para renovar.")
            return redirect(destino)

        plan = request.POST.get("plan") or condominio.plan
        if plan not in settings.PRECIOS_PLAN:
            messages.error(request, "Elige un plan válido antes de pagar.")
            return redirect(destino)

        monto = settings.PRECIOS_PLAN[plan]

        pago = Pago.objects.filter(condominio=condominio, tipo="suscripcion", estado="pendiente").order_by("-fecha_creacion").first()
        if pago:
            pago.monto = monto
            pago.plan = plan
            pago.save(update_fields=["monto", "plan"])
        else:
            pago = Pago.objects.create(condominio=condominio, tipo="suscripcion", monto=monto, plan=plan)

        url_pago = crear_preferencia_pago(pago, request)
        if not url_pago:
            messages.error(request, "No pudimos iniciar el pago. Intenta de nuevo en un momento.")
            return redirect(destino)
        return redirect(url_pago)


class DonarView(LoginRequiredMixin, View):
    """Para que un condominio apoye económicamente el desarrollo de la
    plataforma -- sin relación con su propia suscripción: no extiende
    `pagado_hasta` ni cambia el plan (ver WebhookMercadoPagoView)."""

    def post(self, request, *args, **kwargs):
        membresia = getattr(request.user, "membresia", None)
        if membresia is None:
            messages.error(request, "Tu cuenta no está vinculada a ningún condominio.")
            return redirect("login")

        if membresia.rol != "directiva":
            messages.error(request, "Solo la directiva puede gestionar donaciones.")
            return redirect("mi-condominio")

        if not settings.MERCADOPAGO_ACCESS_TOKEN:
            messages.error(request, "El pago en línea todavía no está disponible. Escríbenos para donar.")
            return redirect("mi-condominio")

        try:
            monto = Decimal((request.POST.get("monto") or "").replace(",", "."))
        except InvalidOperation:
            monto = None
        if not monto or monto <= 0:
            messages.error(request, "Ingresa un monto válido para donar.")
            return redirect("mi-condominio")

        pago = Pago.objects.create(condominio=membresia.condominio, tipo="donacion", monto=monto)
        url_pago = crear_preferencia_pago(pago, request)
        if not url_pago:
            messages.error(request, "No pudimos iniciar la donación. Intenta de nuevo en un momento.")
            return redirect("mi-condominio")
        return redirect(url_pago)


class PagoResultadoView(LoginRequiredMixin, TemplateView):
    """A donde vuelve el navegador tras pagar (o cancelar). Solo informativa
    -- la confirmación real llega por separado a WebhookMercadoPagoView."""

    template_name = "pagos/pago_resultado.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estado"] = self.request.GET.get("status", "")
        return context


@method_decorator(csrf_exempt, name="dispatch")
class WebhookMercadoPagoView(View):
    """Mercado Pago llama acá server-a-server. Nunca se confía en el cuerpo
    del POST: siempre se re-consulta el pago por ID antes de aprobar nada."""

    def post(self, request, *args, **kwargs):
        try:
            datos = json.loads(request.body or "{}")
        except ValueError:
            return HttpResponse(status=400)

        payment_id = (datos.get("data") or {}).get("id") or request.GET.get("id")
        if not payment_id:
            return HttpResponse(status=200)

        detalle = obtener_pago_mercadopago(payment_id)
        if not detalle:
            return HttpResponse(status=200)

        pago = Pago.objects.filter(pk=detalle.get("external_reference")).first()
        if not pago:
            return HttpResponse(status=200)

        estado_mp = detalle.get("status")
        if estado_mp == "approved" and pago.estado != "aprobado":
            pago.estado = "aprobado"
            pago.mercadopago_payment_id = str(payment_id)
            pago.fecha_confirmacion = timezone.now()
            pago.save(update_fields=["estado", "mercadopago_payment_id", "fecha_confirmacion"])

            if pago.tipo == "suscripcion":
                condominio = pago.condominio
                hoy = timezone.localdate()
                desde = condominio.pagado_hasta if condominio.pagado_hasta and condominio.pagado_hasta > hoy else hoy
                condominio.pagado_hasta = desde + datetime.timedelta(days=30)
                condominio.plan = pago.plan
                condominio.save(update_fields=["pagado_hasta", "plan"])
        elif estado_mp == "rejected" and pago.estado == "pendiente":
            pago.estado = "rechazado"
            pago.save(update_fields=["estado"])

        return HttpResponse(status=200)
