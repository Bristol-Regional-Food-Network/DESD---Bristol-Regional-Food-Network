from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from users.decorators import role_required
from .models import Producer


def index(request):
    # optional landing page
    return render(request, "producers/index.html")


@login_required
@role_required("producer")
def dashboard(request):
    producer = getattr(request.user, "producer", None)
    # if you don't have Product linked yet, keep products empty
    my_products = []
    return render(
        request,
        "producers/dashboard.html",
        {"producer": producer, "my_products": my_products},
    )


def list_producers(request):
    producers = Producer.objects.all().order_by("display_name")
    return render(request, "producers/list.html", {"producers": producers})


def producer_detail(request, producer_id):
    producer = get_object_or_404(Producer, id=producer_id)
    return render(request, "producers/detail.html", {"producer": producer})

