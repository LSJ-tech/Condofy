from rest_framework.routers import DefaultRouter

from .api_views import CuotaUnidadViewSet

router = DefaultRouter()
router.register("gastos-comunes", CuotaUnidadViewSet, basename="cuota-unidad")

urlpatterns = router.urls
