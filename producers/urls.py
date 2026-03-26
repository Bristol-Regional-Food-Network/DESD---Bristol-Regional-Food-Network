from django.urls import path
from . import views

app_name = "producers"

urlpatterns = [
    path("", views.index, name="index"),
    path("dashboard/", views.dashboard, name="producer_dashboard"),
    path("orders/", views.producer_orders, name="producer_orders"),
    path("orders/<int:order_id>/", views.producer_order_detail, name="producer_order_detail"),
    path("orders/<int:order_id>/bulk-fulfil/", views.bulk_fulfil_order, name="bulk_fulfil_order"),
    path("orders/items/<int:item_id>/status/", views.update_order_item_status, name="update_order_item_status"),
    path("list/", views.list_producers, name="list"),
    path("<int:producer_id>/", views.producer_detail, name="detail"),
]
