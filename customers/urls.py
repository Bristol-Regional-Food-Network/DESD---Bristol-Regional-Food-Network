from django.urls import path
from .views import dashboard, saved_products, save_product, remove_saved_product

urlpatterns = [
    path("dashboard/", dashboard, name="customer_dashboard"),
    path("saved/", saved_products, name="saved_products"),
    path("save/<int:product_id>/", save_product, name="save_product"),
    path("saved/remove/<int:product_id>/", remove_saved_product, name="remove_saved_product"),
]