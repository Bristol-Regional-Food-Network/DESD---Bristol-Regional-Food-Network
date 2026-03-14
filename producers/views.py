from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from basket.models import OrderItem
from users.decorators import role_required
from .models import Producer
from products.models import Product   # <-- ADD THIS

def _producer_to_dict(producer: Producer):
    return {
        "id": producer.id,
        "display_name": producer.display_name,
        "bio": producer.bio,
        "location": producer.location,
        "phone": producer.phone,
        "website": producer.website,
        "product_count": producer.products.count(),
    }


def index(request):
    return render(request, "producers/index.html")

def index(request):
    return render(request, "producers/index.html")


@login_required
@login_required
@role_required("producer")
def producer_orders(request):
    producer = getattr(request.user, "producer", None)

    if producer is None:
        return render(request, "producers/orders.html", {"order_items": []})

    order_items = (
        OrderItem.objects
        .filter(producer=producer)
        .select_related("order", "product", "order__customer")
        .order_by("-order__created_at")
    )

    return render(
        request,
        "producers/orders.html",
        {
            "producer": producer,
            "order_items": order_items,
        },
    )


def list_producers(request):
    producers = Producer.objects.all().order_by("display_name")
    return render(request, "producers/list.html", {"producers": producers})


def producer_detail(request, producer_id):
    producer = get_object_or_404(Producer, id=producer_id)
    return render(request, "producers/detail.html", {"producer": producer})

@require_http_methods(["GET"])
def api_producer_collection(request: HttpRequest):
    producers = Producer.objects.all().order_by("display_name")
    location = request.GET.get("location")
    if location:
        producers = producers.filter(location__icontains=location)
    return JsonResponse([_producer_to_dict(p) for p in producers], safe=False)


@require_http_methods(["GET"])
def api_producer_resource(request: HttpRequest, producer_id: int):
    producer = get_object_or_404(Producer, id=producer_id)
    data = _producer_to_dict(producer)
    data["products"] = [
        {
            "id": product.id,
            "name": product.name,
            "price": str(product.price),
            "stock": product.stock,
        }
        for product in producer.products.all().order_by("-id")
    ]
    return JsonResponse(data)
