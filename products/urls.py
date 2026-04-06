from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("add/", views.add_product, name="add"),
    path("<int:product_id>/", views.product_detail, name="product_detail"),
    path("<int:product_id>/edit/", views.edit_product, name="edit"),
    path("<int:product_id>/delete/", views.delete_product, name="delete"),
    path("<int:product_id>/review/", views.submit_review, name="submit_review"),
]