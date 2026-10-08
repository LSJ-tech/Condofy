from django.urls import path

from . import views

urlpatterns = [
    path("alertas/historial/", views.AlertaHistorialView.as_view(), name="alertas-historial"),
]
