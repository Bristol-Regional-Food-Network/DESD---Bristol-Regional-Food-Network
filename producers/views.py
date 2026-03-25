from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from users.decorators import role_required
from .models import Producer
from products.models import Product


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


@login_required
@role_required("producer")
def dashboard(request):
    producer = getattr(request.user, "producer", None)

    if producer is None:
        return render(
            request,
            "producers/dashboard.html",
            {
                "producer": None,
                "my_products": [],
                "seasonal_products": [],
                "discounted_products": [],
                "surplus_products": [],
                "all_products": [],
                "upcoming_season_products": [],
            },
        )

    my_products = Product.objects.filter(producer=producer).order_by("-id")
    seasonal_products = my_products.filter(section=Product.SECTION_SEASONAL)
    discounted_products = my_products.filter(section=Product.SECTION_DISCOUNTED)
    surplus_products = my_products.filter(section=Product.SECTION_SURPLUS)
    all_products = my_products.filter(section=Product.SECTION_ALL)
    upcoming_season_products = [p for p in my_products if p.season_starts_next_month]

    return render(
        request,
        "producers/dashboard.html",
        {
            "producer": producer,
            "my_products": my_products,
            "seasonal_products": seasonal_products,
            "discounted_products": discounted_products,
            "surplus_products": surplus_products,
            "all_products": all_products,
            "upcoming_season_products": upcoming_season_products,
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
            "availability_mode": product.availability_mode,
            "season_range_display": product.season_range_display,
            "customer_status": product.customer_status,
            "is_visible_to_customers": product.is_visible_to_customers,
            "is_surplus": product.is_surplus,
            "surplus_discount_percent": product.surplus_discount_percent,
            "surplus_note": product.surplus_note,
            "surplus_expires_at": product.surplus_expires_at.isoformat() if product.surplus_expires_at else None,
            "is_surplus_active": product.is_surplus_active,
            "active_price": str(product.active_price),
        }
        for product in producer.products.all().order_by("-id")
    ]
    return JsonResponse(data)