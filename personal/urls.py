from django.urls import path

from . import views

urlpatterns = [
    path("personal/", views.EmpleadoListView.as_view(), name="empleados"),
    path("personal/nuevo/", views.EmpleadoCreateView.as_view(), name="empleado-crear"),
    path("personal/<int:pk>/editar/", views.EmpleadoUpdateView.as_view(), name="empleado-editar"),
    path("personal/<int:empleado_pk>/liquidaciones/", views.LiquidacionListView.as_view(), name="liquidaciones"),
    path("personal/<int:empleado_pk>/liquidaciones/generar/", views.LiquidacionGenerarView.as_view(), name="liquidacion-generar"),
    path("liquidaciones/<int:pk>/pdf/", views.LiquidacionPDFView.as_view(), name="liquidacion-pdf"),
]
