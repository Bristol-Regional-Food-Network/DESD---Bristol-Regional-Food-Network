from django.urls import path
from . import views

app_name = "basket"

urlpatterns = [
    path("", views.basket_detail, name="basket_detail"),
    path("add/<int:product_id>/", views.basket_add, name="basket_add"),
    path("update/<int:product_id>/", views.basket_update, name="basket_update"),
    path("remove/<int:product_id>/", views.basket_remove, name="basket_remove"),
    path("checkout/", views.checkout, name="checkout"),

    # Order history
    path("orders/", views.order_history, name="order_history"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/reorder/", views.reorder_order, name="reorder_order"),
]