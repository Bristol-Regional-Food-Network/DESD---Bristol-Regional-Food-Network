from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    path("add/", views.add_product, name="add"),
]