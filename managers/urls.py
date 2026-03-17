from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.manager_dashboard, name='manager_dashboard'),
]
