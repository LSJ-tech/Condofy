from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Aviso


@admin.register(Aviso)
class AvisoAdmin(ModelAdmin):
    list_display = ["titulo", "condominio", "autor", "fecha_creacion"]
    list_filter = ["condominio"]
