from django.urls import path
from .views import home, register_customer, register_producer

urlpatterns = [
    path("", home, name="home"),
    path("register/customer/", register_customer, name="register_customer"),
    path("register/producer/", register_producer, name="register_producer"),
]