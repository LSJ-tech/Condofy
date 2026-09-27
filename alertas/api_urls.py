from rest_framework.routers import DefaultRouter

from .api_views import AlertaViewSet

router = DefaultRouter()
router.register("alertas", AlertaViewSet, basename="alerta")

urlpatterns = router.urls
