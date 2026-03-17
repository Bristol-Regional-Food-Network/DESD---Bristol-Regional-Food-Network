from django.urls import path
from .views import home, register_customer, register_producer
from . import admin_views

urlpatterns = [
    path("", home, name="home"),
    path("register/customer/", register_customer, name="register_customer"),
    path("register/producer/", register_producer, name="register_producer"),

    # lightweight admin CRUD for customers/producers/orders (moved to avoid Django admin conflict)
    path("management/", admin_views.admin_dashboard, name="admin_dashboard"),
    path("management/customers/", admin_views.customers_list, name="admin_customers"),
    path("management/customers/<int:user_id>/edit/", admin_views.customer_edit, name="admin_customer_edit"),

    path("management/producers/", admin_views.producers_list, name="admin_producers"),
    path("management/producers/<int:pk>/edit/", admin_views.producer_edit, name="admin_producer_edit"),

    path("management/orders/", admin_views.orders_list, name="admin_orders"),
    path("management/orders/create/", admin_views.order_create, name="admin_order_create"),
    path("management/orders/<int:pk>/", admin_views.order_detail, name="admin_order_detail"),
    path("management/orders/<int:pk>/edit/", admin_views.order_edit, name="admin_order_edit"),
    path("management/orders/<int:pk>/delete/", admin_views.order_delete, name="admin_order_delete"),
]