from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(ModelAdmin):
    list_display = ["condominio", "plan", "monto", "estado", "fecha_creacion"]
    list_filter = ["plan", "estado"]
