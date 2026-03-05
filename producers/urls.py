from django.urls import path
from . import views

app_name = "producers"

urlpatterns = [
    path("", views.index, name="index"),
    path("dashboard/", views.dashboard, name="producer_dashboard"),
    path("list/", views.list_producers, name="list"),
    path("<int:producer_id>/", views.producer_detail, name="detail"),
]