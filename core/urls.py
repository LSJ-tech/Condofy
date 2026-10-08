from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.InicioView.as_view(), name="inicio"),
    path("registro/", views.RegistroCondominioView.as_view(), name="registro-condominio"),
    path("solicitar-acceso/", views.SolicitarAccesoView.as_view(), name="solicitar-acceso"),
    path("unirme/<uuid:token>/", views.RegistroResidenteView.as_view(), name="registro-residente"),
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("suscripcion-vencida/", views.SuscripcionVencidaView.as_view(), name="suscripcion-vencida"),
    path("mi-condominio/", views.CondominioUpdateView.as_view(), name="mi-condominio"),
    path("mi-condominio/qr-residentes.png", views.QRRegistroResidentesView.as_view(), name="qr-registro-residentes"),
    path("mi-condominio/regenerar-link-residentes/", views.RegenerarTokenResidentesView.as_view(), name="regenerar-token-residentes"),
    path("admin-utils/probar-correo/", views.probar_correo, name="probar-correo"),
    path("admin-utils/listar-condominios/", views.listar_condominios, name="listar-condominios"),
    path("admin-utils/cargar-torres-empart/", views.cargar_torres_empart, name="cargar-torres-empart"),
    path("miembros/", views.MiembroListView.as_view(), name="miembros"),
    path("miembros/nuevo/", views.CrearMiembroView.as_view(), name="crear-miembro"),
    path("torres/", views.TorreListView.as_view(), name="torres"),
    path("torres/nueva/", views.TorreCreateView.as_view(), name="crear-torre"),
    path("unidades/", views.UnidadListView.as_view(), name="unidades"),
    path("unidades/nueva/", views.UnidadCreateView.as_view(), name="crear-unidad"),
    path("unidades/aplicar-alicuota/", views.AplicarAlicuotaMasivaView.as_view(), name="aplicar-alicuota-masiva"),
]
