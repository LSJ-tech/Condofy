from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect

MENSAJE_SIN_CONDOMINIO = "Tu cuenta no está vinculada a ningún condominio."


class CondominioRequiredMixin(LoginRequiredMixin):
    """Exige login y restringe las consultas al condominio del usuario logueado.

    A diferencia de NegocioRequiredMixin en PataAgenda, acá no hace falta
    resolver una "sucursal activa" -- un usuario pertenece a un solo
    condominio (no hay selector).
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
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
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(condominio=self.condominio)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["membresia"] = self.membresia
        context["condominio"] = self.condominio
        return context


class CondominioFormMixin(CondominioRequiredMixin):
    """Para crear/editar: asigna el condominio a la instancia antes de guardar."""

    def form_valid(self, form):
        form.instance.condominio = self.condominio
        return super().form_valid(form)


class SoloDirectivaMixin:
    """Mezclar ANTES de CondominioRequiredMixin/CondominioFormMixin: exige rol 'directiva'."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            membresia = getattr(request.user, "membresia", None)
            if membresia and membresia.rol != "directiva":
                messages.error(request, "Esta acción es exclusiva de la directiva.")
                return redirect("inicio")
        return super().dispatch(request, *args, **kwargs)


class SoloDirectivaOConserjeMixin:
    """Mezclar ANTES de CondominioRequiredMixin/CondominioFormMixin: exige rol 'directiva' o 'conserje'."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            membresia = getattr(request.user, "membresia", None)
            if membresia and membresia.rol not in ("directiva", "conserje"):
                messages.error(request, "Esta acción es exclusiva de la directiva/conserjería.")
                return redirect("inicio")
        return super().dispatch(request, *args, **kwargs)


class BorradoSeguroMixin:
    """Evita el error 500 al borrar un registro que otros protegen (on_delete=PROTECT)."""

    mensaje_proteccion = "No se puede eliminar: tiene registros relacionados."

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, self.mensaje_proteccion)
            return redirect(self.success_url)
        messages.success(self.request, f"{self.object} eliminado correctamente.")
        return response
