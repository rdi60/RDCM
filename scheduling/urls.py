from django.urls import path

from . import views

urlpatterns = [
    path("patients/", views.patient_list, name="patient_list"),
    path("patients/new/", views.patient_create, name="patient_create"),
    path("patients/<int:pk>/", views.patient_detail, name="patient_detail"),
    path("appointments/", views.calendar_view, name="calendar"),
    path("appointments/new/", views.appointment_create, name="appointment_create"),
    path("appointments/<int:pk>/", views.appointment_detail, name="appointment_detail"),
    path(
        "appointments/<int:pk>/status/<str:new_status>/",
        views.appointment_set_status,
        name="appointment_set_status",
    ),
]
