from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from users.decorators import role_required
from .models import Producer
from products.models import Product   # <-- ADD THIS


def index(request):
    return render(request, "producers/index.html")


@login_required
@role_required("producer")
def dashboard(request):

    producer = getattr(request.user, "producer", None)

    if producer is None:
        return render(request, "producers/dashboard.html", {
            "producer": None,
            "my_products": []
        })

    # Get products belonging to this producer
    my_products = Product.objects.filter(producer=producer)

    return render(
        request,
        "producers/dashboard.html",
        {
            "producer": producer,
            "my_products": my_products
        },
    )


def list_producers(request):
    producers = Producer.objects.all().order_by("display_name")
    return render(request, "producers/list.html", {"producers": producers})


def producer_detail(request, producer_id):
    producer = get_object_or_404(Producer, id=producer_id)
    return render(request, "producers/detail.html", {"producer": producer})