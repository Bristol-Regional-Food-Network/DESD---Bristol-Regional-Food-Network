from decimal import Decimal, InvalidOperation
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users.decorators import role_required
from .forms import ProductForm
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
        "section": product.section,
        "discount_percent": product.discount_percent,
        "discounted_price": str(product.discounted_price),
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


def _coerce_discount_percent(value, default=0):
    if value is None or value == "":
        return default
    try:
        discount = int(value)
    except (TypeError, ValueError):
        raise ValueError("discount_percent must be an integer.")
    if discount < 0 or discount > 100:
        raise ValueError("discount_percent must be between 0 and 100.")
    return discount


def product_list(request):
    products = Product.objects.select_related("producer").all().order_by("-id")

    seasonal_products = products.filter(section=Product.SECTION_SEASONAL)
    discounted_products = products.filter(section=Product.SECTION_DISCOUNTED)
    all_products = products.filter(section=Product.SECTION_ALL)

    return render(
        request,
        "products/product_list.html",
        {
            "seasonal_products": seasonal_products,
            "discounted_products": discounted_products,
            "all_products": all_products,
        },
    )


def product_detail(request, product_id):
    product = get_object_or_404(Product.objects.select_related("producer"), id=product_id)
    return render(request, "products/product_detail.html", {"product": product})


@login_required
@role_required("producer")
def add_product(request):
    producer = Producer.objects.filter(user=request.user).first()

    if producer is None:
        messages.error(request, "Producer profile not found.")
        return redirect("producers:producer_dashboard")

    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.producer = producer

            if product.section != Product.SECTION_DISCOUNTED:
                product.discount_percent = 0

            product.save()
            messages.success(request, "Product added successfully.")
            return redirect("producers:producer_dashboard")
    else:
        form = ProductForm()

    return render(request, "products/add_product.html", {"form": form, "page_title": "Add Product"})


@login_required
@role_required("producer")
def edit_product(request, product_id):
    producer = Producer.objects.filter(user=request.user).first()
    product = get_object_or_404(Product, id=product_id, producer=producer)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            updated_product = form.save(commit=False)

            if updated_product.section != Product.SECTION_DISCOUNTED:
                updated_product.discount_percent = 0

            updated_product.save()
            messages.success(request, "Product updated successfully.")
            return redirect("producers:producer_dashboard")
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "products/add_product.html",
        {
            "form": form,
            "page_title": "Edit Product",
            "is_edit": True,
            "product": product,
        },
    )


@login_required
@role_required("producer")
def delete_product(request, product_id):
    producer = Producer.objects.filter(user=request.user).first()
    product = get_object_or_404(Product, id=product_id, producer=producer)

    if request.method == "POST":
        product.delete()
        messages.success(request, "Product deleted successfully.")
        return redirect("producers:producer_dashboard")

    return redirect("producers:producer_dashboard")


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
        discount_percent = _coerce_discount_percent(payload.get("discount_percent"), default=0)
    except ValueError as exc:
        return _json_error(str(exc), 400)

    section = str(payload.get("section", Product.SECTION_ALL)).strip() or Product.SECTION_ALL
    if section not in {choice[0] for choice in Product.SECTION_CHOICES}:
        section = Product.SECTION_ALL

    if section != Product.SECTION_DISCOUNTED:
        discount_percent = 0

    product = Product.objects.create(
        producer=producer,
        name=str(payload.get("name", "")).strip(),
        description=str(payload.get("description", "")).strip(),
        price=price,
        stock=stock,
        section=section,
        discount_percent=discount_percent,
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

    if "section" in payload:
        section = str(payload["section"]).strip()
        if section in {choice[0] for choice in Product.SECTION_CHOICES}:
            product.section = section

    if "discount_percent" in payload:
        try:
            product.discount_percent = _coerce_discount_percent(payload["discount_percent"])
        except ValueError as exc:
            return _json_error(str(exc), 400)

    if product.section != Product.SECTION_DISCOUNTED:
        product.discount_percent = 0

    product.save()
    return JsonResponse(_product_to_dict(product))