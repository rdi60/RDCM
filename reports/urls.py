from django.urls import path

from . import views

urlpatterns = [
    path("reports/", views.reports_hub, name="reports_hub"),
    path("reports/footfall/", views.footfall_report, name="footfall_report"),
    path("reports/revenue/", views.revenue_report, name="revenue_report"),
    path("reports/utilization/", views.utilization_report, name="utilization_report"),
    path("reports/inventory/", views.inventory_report, name="inventory_report"),
    path("reports/recall/", views.recall_report, name="recall_report"),
]
