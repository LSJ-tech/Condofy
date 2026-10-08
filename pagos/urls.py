from django.urls import path

from . import views

urlpatterns = [
    path("pago/iniciar/", views.IniciarPagoView.as_view(), name="pago-iniciar"),
    path("donar/", views.DonarView.as_view(), name="donar"),
    path("pago/resultado/", views.PagoResultadoView.as_view(), name="pago-resultado"),
    path("pago/webhook/", views.WebhookMercadoPagoView.as_view(), name="pago-webhook"),
]
