from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('core.urls')),
    path('', include('accesos.urls')),
    path('', include('gastoscomunes.urls')),
    path('', include('pagos.urls')),

    path('api/v1/', include('core.api_urls')),
    path('api/v1/', include('notificaciones.api_urls')),
    path('api/v1/', include('alertas.api_urls')),
    path('api/v1/', include('comunicacion.api_urls')),
    path('api/v1/', include('gastoscomunes.api_urls')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
