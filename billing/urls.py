from django.urls import path

from . import views

urlpatterns = [
    path("billing/invoices/", views.invoice_list, name="invoice_list"),
    path("billing/invoices/new/", views.invoice_create, name="invoice_create"),
    path("billing/invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path(
        "billing/invoices/<int:pk>/items/<int:item_pk>/remove/",
        views.invoice_remove_item,
        name="invoice_remove_item",
    ),
    path("billing/invoices/<int:pk>/print/", views.invoice_print, name="invoice_print"),
    path("billing/payments/<int:pk>/print/", views.payment_print, name="payment_print"),
    path("billing/dues/", views.dues_list, name="dues_list"),
]
