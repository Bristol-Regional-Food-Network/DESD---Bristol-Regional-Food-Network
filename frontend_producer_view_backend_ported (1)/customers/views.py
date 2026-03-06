from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from products.models import Product


def _product_summary(product: Product):
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": str(product.price),
        "stock": product.stock,
        "producer": product.producer.display_name,
    }


def dashboard(request):
    """
    Customer dashboard:
    - product search (read operations)
    - latest products list
    """
    q = request.GET.get("q", "").strip()

    products_qs = Product.objects.select_related("producer").all()

    if q:
        products_qs = products_qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(producer__display_name__icontains=q)
        )

    latest_products = products_qs.order_by("-id")[:9]

    context = {
        "q": q,
        "latest_products": latest_products,
    }
    return render(request, "customers/dashboard.html", context)


@require_http_methods(["GET"])
def api_dashboard_products(request: HttpRequest):
    q = request.GET.get("q", "").strip()
    products_qs = Product.objects.select_related("producer").all().order_by("-id")
    if q:
        products_qs = products_qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(producer__display_name__icontains=q)
        )
    latest_products = products_qs[:20]
    return JsonResponse(
        {
            "query": q,
            "count": latest_products.count() if hasattr(latest_products, "count") else len(latest_products),
            "results": [_product_summary(product) for product in latest_products],
        }
    )
