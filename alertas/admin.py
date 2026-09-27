from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Alerta


@admin.register(Alerta)
class AlertaAdmin(ModelAdmin):
    list_display = ["condominio", "tipo", "estado", "autor", "fecha_creacion"]
    list_filter = ["condominio", "tipo", "estado"]
