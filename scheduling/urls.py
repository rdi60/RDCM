from django.urls import path

from . import views

urlpatterns = [
    path("patients/", views.patient_list, name="patient_list"),
    path("patients/new/", views.patient_create, name="patient_create"),
    path("patients/<int:pk>/", views.patient_detail, name="patient_detail"),
    path("register/", views.self_register, name="self_register"),
    path("register/done/", views.self_register_done, name="self_register_done"),
    path("self-registrations/", views.self_registration_list, name="self_registration_list"),
    path(
        "self-registrations/<int:pk>/",
        views.self_registration_review,
        name="self_registration_review",
    ),
    path("appointments/", views.calendar_view, name="calendar"),
    path("appointments/new/", views.appointment_create, name="appointment_create"),
    path("appointments/<int:pk>/", views.appointment_detail, name="appointment_detail"),
    path(
        "appointments/<int:pk>/status/<str:new_status>/",
        views.appointment_set_status,
        name="appointment_set_status",
    ),
]
