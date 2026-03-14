from django.urls import path
from . import views

app_name = "producers"

urlpatterns = [
    path("", views.dashboard, name="index"),
    path("dashboard/", views.dashboard, name="producer_dashboard"),
    path("orders/", views.producer_orders, name="producer_orders"),
    path("list/", views.list_producers, name="list"),
    path("<int:producer_id>/", views.producer_detail, name="detail"),
]