from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import CuotaUnidad, GastoComun


class CuotaUnidadInline(TabularInline):
    model = CuotaUnidad
    extra = 0
    fields = ["unidad", "monto", "estado", "fecha_pago"]


@admin.register(GastoComun)
class GastoComunAdmin(ModelAdmin):
    list_display = ["condominio", "periodo", "monto_total", "fecha_vencimiento"]
    list_filter = ["condominio"]
    inlines = [CuotaUnidadInline]
