from django.urls import path
from .views import dashboard, my_products, add_product

urlpatterns = [
    path("dashboard/", dashboard, name="producer_dashboard"),
    path("products/", my_products, name="producer_products"),
    path("products/add/", add_product, name="producer_product_add"),
]