from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

from users.decorators import role_required
from .models import Product
from producers.models import Producer


def product_list(request):
    products = Product.objects.select_related("producer").all().order_by("-id")
    return render(request, "products/product_list.html", {"products": products})


def product_detail(request, product_id):
    product = Product.objects.select_related("producer").get(id=product_id)
    return render(request, "products/product_detail.html", {"product": product})


@login_required
@role_required("producer")
def add_product(request):
    producer = Producer.objects.filter(user=request.user).first()

    if producer is None:
        messages.error(request, "Producer profile not found.")
        return redirect("producers:producer_dashboard")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        price = request.POST.get("price", "").strip()

        if not name or not price:
            messages.error(request, "Please provide at least a name and a price.")
            return render(request, "products/add_product.html")

        Product.objects.create(
            producer=producer,
            name=name,
            description=description,
            price=price,
        )

        messages.success(request, "Product added successfully.")
        return redirect("producers:producer_dashboard")

    return render(request, "products/add_product.html")