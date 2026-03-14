from decimal import Decimal, InvalidOperation
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users.decorators import role_required
from .models import Product
from producers.models import Producer


def _json_error(message: str, status: int = 400, **extra):
    payload = {"error": message}
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=status)


def _parse_json(request: HttpRequest):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def _product_to_dict(product: Product):
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": str(product.price),
        "stock": product.stock,
        "producer": {
            "id": product.producer_id,
            "display_name": product.producer.display_name,
        },
    }


def _coerce_price(value):
    try:
        price = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("price must be a valid decimal.")
    if price <= 0:
        raise ValueError("price must be greater than 0.")
    return price


def _coerce_stock(value, default=0):
    if value is None:
        return default
    try:
        stock = int(value)
    except (TypeError, ValueError):
        raise ValueError("stock must be an integer.")
    if stock < 0:
        raise ValueError("stock must be zero or greater.")
    return stock


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

@require_http_methods(["GET", "POST"])
@csrf_exempt
def api_product_collection(request: HttpRequest):
    if request.method == "GET":
        products = Product.objects.select_related("producer").all().order_by("-id")
        producer_id = request.GET.get("producer_id")
        q = request.GET.get("q")
        if producer_id:
            products = products.filter(producer_id=producer_id)
        if q:
            products = products.filter(name__icontains=q)
        return JsonResponse([_product_to_dict(p) for p in products], safe=False)

    payload = _parse_json(request)
    if payload is None:
        return _json_error("Invalid JSON body.", 400)

    required = ["producer_id", "name", "price"]
    missing = [field for field in required if field not in payload or str(payload.get(field)).strip() == ""]
    if missing:
        return _json_error("Missing required fields.", 400, missing=missing)

    try:
        producer = Producer.objects.get(id=payload["producer_id"])
    except Producer.DoesNotExist:
        return _json_error("producer_id not found.", 404)

    try:
        price = _coerce_price(payload.get("price"))
        stock = _coerce_stock(payload.get("stock"), default=0)
    except ValueError as exc:
        return _json_error(str(exc), 400)

    product = Product.objects.create(
        producer=producer,
        name=str(payload.get("name", "")).strip(),
        description=str(payload.get("description", "")).strip(),
        price=price,
        stock=stock,
    )
    return JsonResponse(_product_to_dict(product), status=201)


@csrf_exempt
def api_product_resource(request: HttpRequest, product_id: int):
    try:
        product = Product.objects.select_related("producer").get(id=product_id)
    except Product.DoesNotExist:
        return _json_error("Product not found.", 404)

    if request.method == "GET":
        return JsonResponse(_product_to_dict(product))

    if request.method not in ("PUT", "PATCH", "DELETE"):
        return HttpResponseNotAllowed(["GET", "PUT", "PATCH", "DELETE"])

    if request.method == "DELETE":
        product.delete()
        return JsonResponse({"deleted": True})

    payload = _parse_json(request)
    if payload is None:
        return _json_error("Invalid JSON body.", 400)

    if request.method == "PUT":
        required = ["producer_id", "name", "price", "stock"]
        missing = [field for field in required if field not in payload]
        if missing:
            return _json_error("Missing required fields for PUT.", 400, missing=missing)

    if "producer_id" in payload:
        try:
            product.producer = Producer.objects.get(id=payload["producer_id"])
        except Producer.DoesNotExist:
            return _json_error("producer_id not found.", 404)

    if "name" in payload:
        product.name = str(payload["name"]).strip()
    if "description" in payload:
        product.description = str(payload["description"]).strip()

    if "price" in payload:
        try:
            product.price = _coerce_price(payload["price"])
        except ValueError as exc:
            return _json_error(str(exc), 400)

    if "stock" in payload:
        try:
            product.stock = _coerce_stock(payload["stock"])
        except ValueError as exc:
            return _json_error(str(exc), 400)

    product.save()
    return JsonResponse(_product_to_dict(product))