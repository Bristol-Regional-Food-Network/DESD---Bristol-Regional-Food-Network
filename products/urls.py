from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("add/", views.add_product, name="add"),

    # JSON API endpoints
    path("api/", views.api_product_collection, name="api_collection"),
    path("api/<int:product_id>/", views.api_product_resource, name="api_resource"),
]
