import datetime

from django.contrib import admin
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline

from .models import PLAN_CHOICES, CodigoInvitacion, Condominio, Membresia, SolicitudAcceso, Torre, Unidad

# Unidad/Torre/Membresia son datos operativos de cada condominio -- se
# registran acá porque, a diferencia de PataAgenda, no hay un panel interno
# rico todavía para gestionarlos (Fase 1 usa el panel simple bajo /panel/).


@admin.action(description="Extender 30 días de acceso pagado")
def extender_30_dias(modeladmin, request, queryset):
    hoy = timezone.localdate()
    for condominio in queryset:
        base = condominio.pagado_hasta if condominio.pagado_hasta and condominio.pagado_hasta > hoy else hoy
        condominio.pagado_hasta = base + datetime.timedelta(days=30)
        condominio.save()


def _cambiar_plan(plan):
    @admin.action(description=f"Cambiar a plan {dict(PLAN_CHOICES)[plan]}")
    def accion(modeladmin, request, queryset):
        queryset.update(plan=plan)
    accion.__name__ = f"cambiar_a_{plan}"
    return accion


cambiar_a_free = _cambiar_plan("free")
cambiar_a_premium = _cambiar_plan("premium")


class UnidadInline(TabularInline):
    model = Unidad
    extra = 0
    fields = ["numero", "torre", "alicuota"]


class MembresiaInline(TabularInline):
    model = Membresia
    extra = 0
    autocomplete_fields = ["user"]
    verbose_name = "Usuario vinculado"
    verbose_name_plural = "Usuarios vinculados (directiva / conserjería / residentes)"


@admin.register(Condominio)
class CondominioAdmin(ModelAdmin):
    list_display = ["nombre", "plan", "es_fundador", "estado_suscripcion", "activo", "fecha_creacion"]
    list_filter = ["plan", "es_fundador", "activo"]
    search_fields = ["nombre"]
    actions = [extender_30_dias, cambiar_a_free, cambiar_a_premium]
    inlines = [UnidadInline, MembresiaInline]

    @admin.display(description="Suscripción")
    def estado_suscripcion(self, obj):
        if obj.pagado_hasta is None:
            return "Sin restricción"
        return f"{'Vencida' if obj.esta_vencido else 'Vigente'} hasta {obj.pagado_hasta}"


@admin.register(Torre)
class TorreAdmin(ModelAdmin):
    list_display = ["nombre", "condominio"]
    list_filter = ["condominio"]


@admin.register(Unidad)
class UnidadAdmin(ModelAdmin):
    list_display = ["numero", "condominio", "torre", "alicuota"]
    list_filter = ["condominio"]


@admin.register(Membresia)
class MembresiaAdmin(ModelAdmin):
    list_display = ["user", "condominio", "rol", "unidad"]
    list_filter = ["rol", "condominio"]
    autocomplete_fields = ["user"]


@admin.register(CodigoInvitacion)
class CodigoInvitacionAdmin(ModelAdmin):
    """"Añadir" ya genera un código nuevo solo (ver default del campo) -- basta con Guardar."""

    list_display = ["codigo", "usado_display", "condominio", "fecha_creacion", "fecha_uso"]
    list_filter = ["fecha_creacion"]
    readonly_fields = ["condominio", "fecha_uso"]

    @admin.display(description="Usado", boolean=True)
    def usado_display(self, obj):
        return obj.usado


@admin.action(description="Marcar como atendido")
def marcar_atendido(modeladmin, request, queryset):
    queryset.update(atendido=True)


@admin.register(SolicitudAcceso)
class SolicitudAccesoAdmin(ModelAdmin):
    list_display = ["condominio", "nombre", "comuna", "telefono", "atendido", "fecha_creacion"]
    list_filter = ["atendido", "comuna"]
    search_fields = ["nombre", "condominio", "telefono", "email"]
    actions = [marcar_atendido]
