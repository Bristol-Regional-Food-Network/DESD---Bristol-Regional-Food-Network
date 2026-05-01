from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('orders/', views.orders_list, name='manager_orders'),
    path('customers/', views.customers_list, name='manager_customers'),
    path('producers/', views.producers_list, name='manager_producers'),

    # TC-025: Financial Reports / Network Commission
    path('financial-reports/', views.financial_reports, name='manager_financial_reports'),
    path('financial-reports/<int:order_id>/', views.financial_report_detail, name='manager_financial_report_detail'),
]
