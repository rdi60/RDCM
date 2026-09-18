from rest_framework.routers import DefaultRouter

from .views import AppointmentViewSet, TreatmentPlanViewSet

router = DefaultRouter()
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register("treatment-plans", TreatmentPlanViewSet, basename="treatment-plan")

urlpatterns = router.urls
