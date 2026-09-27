from django.urls import path

from . import api_views

urlpatterns = [
    path("dispositivos/", api_views.DispositivoPushCreateView.as_view(), name="api-dispositivos"),
]
