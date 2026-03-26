from decimal import Decimal, InvalidOperation
import json
import math
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users.decorators import role_required
from .forms import ProductForm
from .models import Product
from producers.models import Producer


POSTCODE_COORDS = {
    "BS1": (51.4545, -2.5879),
    "BS2": (51.4590, -2.5850),
    "BS3": (51.4416, -2.6010),
    "BS4": (51.4340, -2.5610),
    "BS5": (51.4620, -2.5480),
    "BS6": (51.4700, -2.6100),
    "BS7": (51.4860, -2.5910),
    "BS8": (51.4580, -2.6200),
    "BS9": (51.4850, -2.6310),
    "BS10": (51.5050, -2.6210),
    "BS11": (51.4950, -2.6750),
    "BS13": (51.4120, -2.6110),
    "BS14": (51.4140, -2.5590),
    "BS15": (51.4570, -2.5050),
    "BS16": (51.4860, -2.5110),
    "BS20": (51.4790, -2.7640),
    "BS21": (51.4380, -2.8500),
    "BS22": (51.3590, -2.9280),
    "BS23": (51.3460, -2.9770),
    "BS24": (51.3270, -2.9310),
    "BS30": (51.4460, -2.4720),
    "BS31": (51.4070, -2.4950),
    "BS32": (51.5430, -2.5620),
    "BS34": (51.5250, -2.5640),
    "BS35": (51.6040, -2.5470),
    "BS36": (51.5260, -2.4860),
    "BS37": (51.5400, -2.4180),
    "BS39": (51.3280, -2.4980),
    "BS40": (51.3810, -2.6900),
    "BS41": (51.4300, -2.6520),
    "BS48": (51.4260, -2.7480),
    "BS49": (51.3820, -2.8170),
    "BA1": (51.3870, -2.3590),
    "BA2": (51.3590, -2.3880),
    "GL12": (51.6200, -2.3800),
    "SN14": (51.5100, -2.1900),
}


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


def _normalise_postcode(postcode):
    if not postcode:
        return ""
    cleaned = re.sub(r"\s+", "", str(postcode).upper())
    return cleaned


def _postcode_area(postcode):
    cleaned = _normalise_postcode(postcode)
    match = re.match(r"^[A-Z]{1,2}\d{1,2}[A-Z]?", cleaned)
    return match.group(0) if match else ""


def _haversine_miles(lat1, lon1, lat2, lon2):
    radius_miles = 3958.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_miles * c


def _estimate_food_miles(customer_postcode, producer_postcode):
    customer_area = _postcode_area(customer_postcode)
    producer_area = _postcode_area(producer_postcode)

    if not customer_area or not producer_area:
        return None

    customer_coords = POSTCODE_COORDS.get(customer_area)
    producer_coords = POSTCODE_COORDS.get(producer_area)

    if not customer_coords or not producer_coords:
        return None

    miles = _haversine_miles(
        customer_coords[0],
        customer_coords[1],
        producer_coords[0],
        producer_coords[1],
    )
    return round(miles, 1)


def _product_to_dict(product: Product):
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": str(product.price),
        "stock": product.stock,
        "section": product.section,
        "category": product.category,
        "category_display": product.get_category_display(),
        "discount_percent": product.discount_percent,
        "discounted_price": str(product.discounted_price),
        "availability_label": product.availability_label,
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
    selected_category = request.GET.get("category", "all")
    q = request.GET.get("q", "").strip()

    products = Product.objects.select_related("producer").filter(stock__gt=0).order_by("-id")

    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(producer__display_name__icontains=q)
        ).distinct()

    if selected_category != "all":
        products = products.filter(category=selected_category)

    seasonal_products = products.filter(section=Product.SECTION_SEASONAL)
    discounted_products = products.filter(section=Product.SECTION_DISCOUNTED)
    all_products = products

    categories = [
        ("all", "All Categories"),
        (Product.CATEGORY_VEGETABLES, "Vegetables"),
        (Product.CATEGORY_FRUITS, "Fruits"),
        (Product.CATEGORY_DAIRY, "Dairy Products"),
        (Product.CATEGORY_BAKERY, "Bakery Goods"),
        (Product.CATEGORY_PRESERVES, "Preserves"),
        (Product.CATEGORY_SEASONAL_SPECIALITIES, "Seasonal Specialities"),
    ]

    return render(
        request,
        "products/product_list.html",
        {
            "seasonal_products": seasonal_products,
            "discounted_products": discounted_products,
            "all_products": all_products,
            "categories": categories,
            "selected_category": selected_category,
            "query": q,
        },
    )


def product_detail(request, product_id):
    product = get_object_or_404(Product.objects.select_related("producer"), id=product_id)

    postcode_param = request.GET.get("postcode", "").strip()
    if postcode_param:
        request.session["customer_postcode"] = postcode_param
        request.session.modified = True

    customer_postcode = request.session.get("customer_postcode", "")
    producer_postcode = getattr(product.producer, "postcode", "")
    food_miles = _estimate_food_miles(customer_postcode, producer_postcode)

    return render(
        request,
        "products/product_detail.html",
        {
            "product": product,
            "customer_postcode": customer_postcode,
            "food_miles": food_miles,
        },
    )


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
        category = request.GET.get("category")

        if producer_id:
            products = products.filter(producer_id=producer_id)
        if q:
            products = products.filter(
                Q(name__icontains=q) |
                Q(description__icontains=q) |
                Q(producer__display_name__icontains=q)
            ).distinct()
        if category:
            products = products.filter(category=category)

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

    category = str(payload.get("category", Product.CATEGORY_VEGETABLES)).strip() or Product.CATEGORY_VEGETABLES
    if category not in {choice[0] for choice in Product.CATEGORY_CHOICES}:
        category = Product.CATEGORY_VEGETABLES

    if section != Product.SECTION_DISCOUNTED:
        discount_percent = 0

    product = Product.objects.create(
        producer=producer,
        name=str(payload.get("name", "")).strip(),
        description=str(payload.get("description", "")).strip(),
        price=price,
        stock=stock,
        section=section,
        category=category,
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

    if "category" in payload:
        category = str(payload["category"]).strip()
        if category in {choice[0] for choice in Product.CATEGORY_CHOICES}:
            product.category = category

    if "discount_percent" in payload:
        try:
            product.discount_percent = _coerce_discount_percent(payload["discount_percent"])
        except ValueError as exc:
            return _json_error(str(exc), 400)

    if product.section != Product.SECTION_DISCOUNTED:
        product.discount_percent = 0

    product.save()
    return JsonResponse(_product_to_dict(product))