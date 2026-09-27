from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import RegistroIngreso


@admin.register(RegistroIngreso)
class RegistroIngresoAdmin(ModelAdmin):
    list_display = ["nombre_visitante", "unidad", "motivo", "fecha_ingreso", "fecha_salida"]
    list_filter = ["motivo", "unidad__condominio"]
