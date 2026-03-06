from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

from users.decorators import role_required
from .models import Product


@login_required
@role_required("producer")
def add_product(request):
    producer = getattr(request.user, "producer", None)

    # If role_required let someone through but profile missing, don't crash
    if producer is None:
        messages.error(request, "Producer profile not found. Please complete producer registration.")
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