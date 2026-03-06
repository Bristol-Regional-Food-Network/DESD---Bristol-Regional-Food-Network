from django.urls import path
from .views import dashboard, api_dashboard_products

urlpatterns = [
    path("dashboard/", dashboard, name="customer_dashboard"),
    path("api/dashboard-products/", api_dashboard_products, name="api_customer_dashboard_products"),
]
