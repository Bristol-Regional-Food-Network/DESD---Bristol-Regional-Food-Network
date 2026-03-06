from django.shortcuts import render

def home(request):
    return render(request, "marketplace/home.html")

def register_customer(request):
    return render(request, "auth/register_customer.html")

def register_producer(request):
    return render(request, "auth/register_producer.html")