from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse

from users.decorators import role_required
from producers.models import Producer
from .forms import ProductForm

@login_required
@role_required("producer")
def add_product(request):
    # Create Producer profile if missing
    producer, _ = Producer.objects.get_or_create(
        user=request.user,
        defaults={"display_name": request.user.get_full_name() or request.user.username},
    )

    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.producer = producer
            product.save()
            return redirect(reverse("producers:producer_dashboard"))
    else:
        form = ProductForm()

    return render(request, "products/add_product.html", {"form": form})