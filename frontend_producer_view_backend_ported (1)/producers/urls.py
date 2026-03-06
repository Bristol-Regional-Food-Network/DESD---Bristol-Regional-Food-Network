from django.urls import path
from . import views

app_name = "producers"

urlpatterns = [
    path("", views.dashboard, name="index"),
    path("dashboard/", views.dashboard, name="producer_dashboard"),
    path("list/", views.list_producers, name="list"),
    path("<int:producer_id>/", views.producer_detail, name="detail"),

    # JSON API endpoints
    path("api/", views.api_producer_collection, name="api_collection"),
    path("api/<int:producer_id>/", views.api_producer_resource, name="api_resource"),
]
