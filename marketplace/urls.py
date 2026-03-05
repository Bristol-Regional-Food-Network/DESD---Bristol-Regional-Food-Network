from django.urls import path

from . import api_views
from . import api_customers, api_inventory, api_orders

urlpatterns = [
    # existing
    path("health/", api_views.health, name="api_health"),
    path("producers/", api_views.producers_list, name="api_producers_list"),
    path("categories/", api_views.categories_list, name="api_categories_list"),
    path("products/", api_views.products_collection, name="api_products_collection"),
    path("products/<int:product_id>/", api_views.product_resource, name="api_product_resource"),

    # new
    path("customers/", api_customers.customers_collection, name="api_customers_collection"),
    path("customers/<int:customer_id>/", api_customers.customer_resource, name="api_customer_resource"),

    path("products/<int:product_id>/inventory/", api_inventory.product_inventory_resource, name="api_product_inventory_resource"),

    path("orders/", api_orders.orders_collection, name="api_orders_collection"),
    path("orders/<int:order_id>/", api_orders.order_resource, name="api_order_resource"),
    path("orders/<int:order_id>/payment/", api_orders.order_payment_resource, name="api_order_payment_resource"),
]
