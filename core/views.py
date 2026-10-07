from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, FormView, ListView, TemplateView, UpdateView

from .forms import CondominioForm, CrearMiembroForm, RegistroCondominioForm, TorreForm, UnidadForm
from .mixins import MENSAJE_SIN_CONDOMINIO, CondominioFormMixin, CondominioRequiredMixin, SoloDirectivaMixin
from .models import Condominio, Membresia, Torre, Unidad
from .usuarios import generar_password_temporal, generar_username

DIAS_PRUEBA_GRATIS = 15


@staff_member_required
def probar_correo(request):
    """Diagnóstico manual: confirma que RESEND_API_KEY está bien configurada en el hosting."""
    destino = request.GET.get("destino")
    if not destino:
        return HttpResponse("Agrega ?destino=tu@email.com a la URL.", status=400)
    send_mail(
        subject="Correo de prueba de Condofy",
        message="Si recibiste esto, el envío de correo (Resend) está funcionando correctamente.",
        from_email=None,
        recipient_list=[destino],
    )
    return HttpResponse(f"Correo de prueba enviado a {destino}.")


class RegistroCondominioView(FormView):
    template_name = "core/registro_condominio.html"
    form_class = RegistroCondominioForm

    def form_valid(self, form):
        datos = form.cleaned_data
        username = generar_username(datos["nombre"], datos["apellido"])
        with transaction.atomic():
            condominio = Condominio.objects.create(
                nombre=datos["nombre_condominio"],
                direccion=datos.get("direccion_condominio", ""),
                comuna=datos.get("comuna_condominio", ""),
                region=datos.get("region_condominio", ""),
                plan="premium",
                pagado_hasta=timezone.localdate() + timezone.timedelta(days=DIAS_PRUEBA_GRATIS),
            )
            user = User.objects.create_user(
                username=username, password=datos["password1"],
                first_name=datos["nombre"], last_name=datos["apellido"],
            )
            Membresia.objects.create(user=user, condominio=condominio, rol="directiva")

        login(self.request, user)
        messages.success(
            self.request,
            f"¡Listo! Creamos la cuenta de {condominio.nombre}. Tu usuario es «{username}» — anótalo, lo necesitas "
            f"para volver a entrar. Tienes {DIAS_PRUEBA_GRATIS} días Pro gratis.",
        )
        return redirect("inicio")


class InicioView(TemplateView):
    """
    La raíz del sitio hace dos trabajos distintos según quién la visite:
    sin sesión, es la landing comercial; con sesión y condominio, es el
    dashboard interno. No se puede resolver con CondominioRequiredMixin
    porque ese mixin exige login antes de decidir nada.
    """

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            self.template_name = "core/landing.html"
            return super().get(request, *args, **kwargs)

        membresia = getattr(request.user, "membresia", None)
        if membresia is None:
            if request.user.is_staff:
                return redirect("admin:index")
            messages.error(request, MENSAJE_SIN_CONDOMINIO)
            return redirect("login")
        if not membresia.condominio.puede_operar:
            return redirect("suscripcion-vencida")

        self.membresia = membresia
        self.condominio = membresia.condominio
        self.template_name = "core/inicio.html"
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, "membresia"):
            context["membresia"] = self.membresia
            context["condominio"] = self.condominio
        else:
            context["dias_prueba_gratis"] = DIAS_PRUEBA_GRATIS
        return context


class SuscripcionVencidaView(TemplateView):
    template_name = "core/suscripcion_vencida.html"


class MiembroListView(SoloDirectivaMixin, CondominioRequiredMixin, ListView):
    template_name = "core/miembro_list.html"
    context_object_name = "membresias"

    def get_queryset(self):
        return Membresia.objects.filter(condominio=self.condominio).select_related("user", "unidad").order_by("rol", "user__last_name")


class CrearMiembroView(SoloDirectivaMixin, CondominioRequiredMixin, FormView):
    template_name = "core/miembro_form.html"
    form_class = CrearMiembroForm
    success_url = reverse_lazy("miembros")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.condominio
        return kwargs

    def form_valid(self, form):
        datos = form.cleaned_data
        username = generar_username(datos["nombre"], datos["apellido"])
        password = generar_password_temporal()
        with transaction.atomic():
            user = User.objects.create_user(
                username=username, password=password,
                first_name=datos["nombre"], last_name=datos["apellido"], email=datos.get("email", ""),
            )
            Membresia.objects.create(
                user=user, condominio=self.condominio, rol=datos["rol"],
                unidad=datos.get("unidad"),
            )
        messages.success(
            self.request,
            f"Cuenta creada: usuario «{username}», contraseña temporal «{password}» — entrégasela a la persona, "
            "no queda guardada en ningún otro lado.",
        )
        return super().form_valid(form)


class CondominioUpdateView(SoloDirectivaMixin, CondominioRequiredMixin, UpdateView):
    model = Condominio
    form_class = CondominioForm
    template_name = "core/condominio_form.html"
    success_url = reverse_lazy("mi-condominio")

    def get_object(self, queryset=None):
        return self.condominio


class TorreListView(SoloDirectivaMixin, CondominioFormMixin, ListView):
    model = Torre
    template_name = "core/torre_list.html"
    context_object_name = "torres"


class TorreCreateView(SoloDirectivaMixin, CondominioFormMixin, CreateView):
    model = Torre
    form_class = TorreForm
    template_name = "core/torre_form.html"
    success_url = reverse_lazy("torres")


class UnidadListView(SoloDirectivaMixin, CondominioFormMixin, ListView):
    model = Unidad
    template_name = "core/unidad_list.html"
    context_object_name = "unidades"

    def get_queryset(self):
        return super().get_queryset().select_related("torre")


class UnidadCreateView(SoloDirectivaMixin, CondominioFormMixin, CreateView):
    model = Unidad
    form_class = UnidadForm
    template_name = "core/unidad_form.html"
    success_url = reverse_lazy("unidades")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["condominio"] = self.condominio
        return kwargs

    def form_valid(self, form):
        if not self.condominio.puede_agregar_unidad:
            messages.error(self.request, "Alcanzaste el límite de unidades de tu plan actual.")
            return redirect("unidades")
        return super().form_valid(form)
