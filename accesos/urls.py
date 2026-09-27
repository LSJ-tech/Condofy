from django.urls import path

from . import views

urlpatterns = [
    path("accesos/", views.RegistroIngresoListView.as_view(), name="registro-ingreso-list"),
    path("accesos/nuevo/", views.RegistroIngresoCreateView.as_view(), name="registro-ingreso-crear"),
    path("accesos/<int:pk>/salida/", views.RegistrarSalidaView.as_view(), name="registro-ingreso-salida"),
]
