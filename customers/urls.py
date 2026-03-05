from django.urls import path
from .views import dashboard

urlpatterns = [
    path("dashboard/", dashboard, name="customer_dashboard"),
]