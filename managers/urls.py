from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('orders/', views.orders_list, name='manager_orders'),
    path('customers/', views.customers_list, name='manager_customers'),
    path('producers/', views.producers_list, name='manager_producers'),
]
