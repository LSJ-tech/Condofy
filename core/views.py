from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.http import require_GET
from django.views.generic import CreateView, FormView, ListView, TemplateView, UpdateView

from .forms import CondominioForm, CrearMiembroForm, RegistroCondominioForm, SolicitudAccesoForm, TorreForm, UnidadForm
from .mixins import MENSAJE_SIN_CONDOMINIO, CondominioFormMixin, CondominioRequiredMixin, SoloDirectivaMixin
from .models import CodigoInvitacion, Condominio, Membresia, Torre, Unidad
from .usuarios import generar_password_temporal, generar_username

EMAIL_CONTACTO_DEVQUAD = "contacto@devquad.cl"

DIAS_PRUEBA_GRATIS = 15


@staff_member_required
@require_GET
def probar_correo(request):
    """Diagnóstico manual: confirma que RESEND_API_KEY está bien configurada en el hosting."""
    destino = request.GET.get("destino", "")
    try:
        validate_email(destino)
    except ValidationError:
        return HttpResponse("Agrega ?destino=tu@email.com (una dirección válida) a la URL.", status=400)
    send_mail(
        subject="Correo de prueba de Condofy",
        message="Si recibiste esto, el envío de correo (Resend) está funcionando correctamente.",
        from_email=None,
        recipient_list=[destino],
    )
    return HttpResponse(f"Correo de prueba enviado a {escape(destino)}.")


@staff_member_required
@require_GET
def listar_condominios(request):
    """Diagnóstico manual: nombre exacto, torres y unidades de cada condominio real en esta base de datos."""
    lineas = []
    for condominio in Condominio.objects.order_by("nombre"):
        lineas.append(
            f"id={condominio.pk} | nombre={condominio.nombre!r} | torres={condominio.torres.count()} | "
            f"unidades={condominio.unidades.count()} | miembros={condominio.membresias.count()}"
        )
    return HttpResponse("\n".join(lineas) or "No hay condominios.", content_type="text/plain; charset=utf-8")


@staff_member_required
@require_GET
def cargar_torres_empart(request):
    """
    Uso único: completa el condominio real "Empart" en producción con sus
    16 torres confirmadas x 5 pisos x 4 deptos (320 unidades). Idempotente
    (get_or_create) -- correrla más de una vez no duplica nada. No toca
    miembros ni unidades que ya existan.
    """
    try:
        condominio = Condominio.objects.get(nombre="Empart")
    except Condominio.DoesNotExist:
        return HttpResponse("No existe un condominio con nombre exacto 'Empart'.", status=404)

    numeros_por_piso = ["1", "2", "3", "4"]
    pisos = ["1", "2", "3", "4", "5"]
    torres_nombres = [str(n) for n in range(1, 17)]

    torres_creadas = 0
    unidades_creadas = 0
    with transaction.atomic():
        for nombre_torre in torres_nombres:
            torre, creada = Torre.objects.get_or_create(condominio=condominio, nombre=nombre_torre)
            if creada:
                torres_creadas += 1
            for piso in pisos:
                for posicion in numeros_por_piso:
                    numero = f"{piso}{posicion}"
                    _, creada = Unidad.objects.get_or_create(condominio=condominio, torre=torre, numero=numero)
                    if creada:
                        unidades_creadas += 1

    return HttpResponse(
        f"Listo. Torres nuevas: {torres_creadas} (de 16). Unidades nuevas: {unidades_creadas} (de 320 esperadas)."
    )


class SolicitarAccesoView(FormView):
    """Formulario público embebido en la landing -- captura el interés de quien todavía no tiene código."""

    template_name = "core/registro_condominio.html"  # no se usa directo: el form vive embebido en landing.html
    form_class = SolicitudAccesoForm
    success_url = reverse_lazy("inicio")

    def form_valid(self, form):
        solicitud = form.save()
        try:
            send_mail(
                subject=f"Nueva solicitud de acceso a Condofy: {solicitud.condominio}",
                message=(
                    f"Nombre: {solicitud.nombre}\nCondominio: {solicitud.condominio}\nComuna: {solicitud.comuna}\n"
                    f"Teléfono: {solicitud.telefono}\nEmail: {solicitud.email}\nMensaje: {solicitud.mensaje}\n\n"
                    f"Gestionar en /admin/core/solicitudacceso/"
                ),
                from_email=None,
                recipient_list=[EMAIL_CONTACTO_DEVQUAD],
            )
        except Exception:
            pass  # el lead ya quedó guardado -- el correo es solo un aviso, no bloquea la solicitud
        messages.success(self.request, "¡Gracias! Recibimos tu solicitud y te vamos a contactar pronto.")
        return redirect("inicio")

    def form_invalid(self, form):
        messages.error(self.request, "No pudimos enviar tu solicitud — revisa los datos e inténtalo de nuevo.")
        return redirect("inicio")


class RegistroCondominioView(FormView):
    template_name = "core/registro_condominio.html"
    form_class = RegistroCondominioForm

    def form_valid(self, form):
        datos = form.cleaned_data
        username = generar_username(datos["nombre"], datos["apellido"])
        with transaction.atomic():
            codigo_obj = CodigoInvitacion.objects.select_for_update().get(pk=form.codigo_obj.pk)
            if codigo_obj.condominio_id is not None:
                messages.error(self.request, "Ese código de invitación ya fue usado.")
                return redirect("registro-condominio")

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
            codigo_obj.condominio = condominio
            codigo_obj.fecha_uso = timezone.now()
            codigo_obj.save()

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
