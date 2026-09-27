from unfold.admin import ModelAdmin
from django.contrib import admin

from .models import DispositivoPush


@admin.register(DispositivoPush)
class DispositivoPushAdmin(ModelAdmin):
    list_display = ["user", "plataforma", "fecha_registro"]
    list_filter = ["plataforma"]
    search_fields = ["user__username", "token"]
