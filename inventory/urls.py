from django.urls import path

from . import views

urlpatterns = [
    path("inventory/stock/", views.stock_levels, name="stock_levels"),
    path("inventory/alerts/", views.alerts, name="inventory_alerts"),
    path("inventory/purchase-orders/", views.po_list, name="po_list"),
    path("inventory/purchase-orders/new/", views.po_create, name="po_create"),
    path("inventory/purchase-orders/<int:pk>/", views.po_detail, name="po_detail"),
    path("inventory/transfers/new/", views.transfer_create, name="transfer_create"),
    path("inventory/consumption/new/", views.consumption_create, name="consumption_create"),
]
