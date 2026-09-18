from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/patients/", include("apps.patients.urls")),
    path("api/scheduling/", include("apps.scheduling.urls")),
]
