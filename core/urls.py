from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("mfa/setup/", views.mfa_setup, name="mfa_setup"),
    path("mfa/setup/qr/", views.mfa_qr, name="mfa_qr"),
    path("mfa/verify/", views.mfa_verify, name="mfa_verify"),
]
