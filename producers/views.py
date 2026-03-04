from django.shortcuts import render, redirect
from django import forms
from users.decorators import role_required
from .models import Producer
from products.models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "description", "price", "available_from", "available_to"]

@role_required("producer")
def dashboard(request):
    producer = Producer.objects.filter(user=request.user).first()
    my_products = Product.objects.filter(producer=producer).count() if producer else 0
    return render(request, "producers/dashboard.html", {"producer": producer, "my_products": my_products})

@role_required("producer")
def my_products(request):
    producer = Producer.objects.filter(user=request.user).first()
    products = Product.objects.filter(producer=producer).order_by("-id") if producer else []
    return render(request, "producers/my_products.html", {"products": products})

@role_required("producer")
def add_product(request):
    producer = Producer.objects.filter(user=request.user).first()
    if not producer:
        # If producer profile not created yet, send them to dashboard (you can improve later)
        return redirect("producer_dashboard")

    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.producer = producer
            product.save()
            return redirect("producer_products")
    else:
        form = ProductForm()

    return render(request, "producers/product_form.html", {"form": form})