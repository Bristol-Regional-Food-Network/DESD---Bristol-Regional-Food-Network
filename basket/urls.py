from django.urls import path
from . import views

app_name = "basket"

urlpatterns = [
    path("", views.basket_detail, name="basket_detail"),
    path("add/<int:product_id>/", views.basket_add, name="basket_add"),
    path("update/<int:product_id>/", views.basket_update, name="basket_update"),
    path("remove/<int:product_id>/", views.basket_remove, name="basket_remove"),
    path("checkout/", views.checkout, name="checkout"),

    path("distance-map/", views.basket_distance_map_api, name="basket_distance_map_api"),
    
    # Order history
    path("orders/", views.order_history, name="order_history"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/reorder/", views.reorder_order, name="reorder_order"),

    # TC-018: Recurring orders
    path("recurring/", views.recurring_orders_list, name="recurring_orders_list"),
    path("recurring/<int:recurring_id>/", views.recurring_order_detail, name="recurring_order_detail"),
    path("recurring/<int:recurring_id>/modify/", views.recurring_order_modify_next, name="recurring_order_modify"),
    path("recurring/<int:recurring_id>/pause/", views.recurring_order_pause, name="recurring_order_pause"),
    path("recurring/<int:recurring_id>/cancel/", views.recurring_order_cancel, name="recurring_order_cancel"),
]