from decimal import Decimal, InvalidOperation
from datetime import timedelta
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
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
        "availability_mode": product.availability_mode,
        "season_start_month": product.season_start_month,
        "season_end_month": product.season_end_month,
        "season_range_display": product.season_range_display,
        "customer_status": product.customer_status,
        "is_visible_to_customers": product.is_visible_to_customers,
        "best_before_date": product.best_before_date.isoformat() if product.best_before_date else None,
        "is_surplus": product.is_surplus,
        "surplus_discount_percent": product.surplus_discount_percent,
        "surplus_note": product.surplus_note,
        "surplus_expires_at": product.surplus_expires_at.isoformat() if product.surplus_expires_at else None,
        "is_surplus_active": product.is_surplus_active,
        "active_price": str(product.active_price),
        "surplus_time_remaining": product.surplus_time_remaining,
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


def _coerce_surplus_discount_percent(value, default=0):
    if value is None or value == "":
        return default
    try:
        discount = int(value)
    except (TypeError, ValueError):
        raise ValueError("surplus_discount_percent must be an integer.")
    if discount < 10 or discount > 50:
        raise ValueError("surplus_discount_percent must be between 10 and 50.")
    return discount


def _coerce_availability_mode(value, default=Product.AVAILABILITY_YEAR_ROUND):
    if value is None or value == "":
        return default

    valid_choices = {choice[0] for choice in Product.AVAILABILITY_CHOICES}
    if value not in valid_choices:
        raise ValueError("availability_mode is invalid.")
    return value


def _coerce_month(value):
    if value in (None, ""):
        return None
    try:
        month = int(value)
    except (TypeError, ValueError):
        raise ValueError("Season month must be an integer.")
    if month < 1 or month > 12:
        raise ValueError("Season month must be between 1 and 12.")
    return month


def _visible_products_queryset():
    products = Product.objects.select_related("producer").all().order_by("-id")
    return [product for product in products if product.is_visible_to_customers]


def product_list(request):
    visible_products = _visible_products_queryset()

    surplus_products = [p for p in visible_products if p.is_surplus_active]
    seasonal_products = [
        p for p in visible_products
        if p.section == Product.SECTION_SEASONAL and not p.is_surplus_active
    ]
    discounted_products = [
        p for p in visible_products
        if p.section == Product.SECTION_DISCOUNTED and not p.is_surplus_active
    ]
    all_products = [
        p for p in visible_products
        if p.section == Product.SECTION_ALL and not p.is_surplus_active
    ]

    return render(
        request,
        "products/product_list.html",
        {
            "surplus_products": surplus_products,
            "seasonal_products": seasonal_products,
            "discounted_products": discounted_products,
            "all_products": all_products,
        },
    )


def product_detail(request, product_id):
    product = get_object_or_404(Product.objects.select_related("producer"), id=product_id)

    owns_product = (
        request.user.is_authenticated
        and hasattr(request.user, "producer")
        and request.user.producer == product.producer
    )

    if not product.is_visible_to_customers and not owns_product:
        messages.error(request, "This product is currently not available for customers.")
        return redirect("products:product_list")

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

            surplus_duration_hours = form.cleaned_data.get("surplus_duration_hours")

            if product.is_surplus:
                product.surplus_expires_at = timezone.now() + timedelta(hours=surplus_duration_hours)
                product.section = Product.SECTION_SURPLUS
            else:
                product.surplus_discount_percent = 0
                product.surplus_note = ""
                product.surplus_expires_at = None

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

            if updated_product.section != Product.SECTION_DISCOUNTED and not updated_product.is_surplus:
                updated_product.discount_percent = 0

            surplus_duration_hours = form.cleaned_data.get("surplus_duration_hours")

            if updated_product.is_surplus:
                if surplus_duration_hours:
                    updated_product.surplus_expires_at = timezone.now() + timedelta(hours=surplus_duration_hours)
                updated_product.section = Product.SECTION_SURPLUS
            else:
                updated_product.surplus_discount_percent = 0
                updated_product.surplus_note = ""
                updated_product.surplus_expires_at = None

            updated_product.save()
            messages.success(request, "Product updated successfully.")
            return redirect("producers:producer_dashboard")
    else:
        initial = {}
        if product.is_surplus_active and product.surplus_expires_at:
            delta = product.surplus_expires_at - timezone.now()
            hours = max(1, int(delta.total_seconds() // 3600))
            initial["surplus_duration_hours"] = hours
        form = ProductForm(instance=product, initial=initial)

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
        visible_only = request.GET.get("visible_only")

        if producer_id:
            products = products.filter(producer_id=producer_id)
        if q:
            products = products.filter(name__icontains=q)

        product_list_result = list(products)
        if visible_only == "true":
            product_list_result = [p for p in product_list_result if p.is_visible_to_customers]

        return JsonResponse([_product_to_dict(p) for p in product_list_result], safe=False)

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
        surplus_discount_percent = _coerce_surplus_discount_percent(payload.get("surplus_discount_percent"), default=0) if payload.get("is_surplus") else 0
        availability_mode = _coerce_availability_mode(payload.get("availability_mode"))
        season_start_month = _coerce_month(payload.get("season_start_month"))
        season_end_month = _coerce_month(payload.get("season_end_month"))
    except ValueError as exc:
        return _json_error(str(exc), 400)

    if availability_mode == Product.AVAILABILITY_SEASONAL and (not season_start_month or not season_end_month):
        return _json_error("Seasonal products require both season_start_month and season_end_month.", 400)

    if availability_mode != Product.AVAILABILITY_SEASONAL:
        season_start_month = None
        season_end_month = None

    section = str(payload.get("section", Product.SECTION_ALL)).strip() or Product.SECTION_ALL
    if section not in {choice[0] for choice in Product.SECTION_CHOICES}:
        section = Product.SECTION_ALL

    is_surplus = bool(payload.get("is_surplus", False))
    surplus_note = str(payload.get("surplus_note", "")).strip()
    best_before_date = payload.get("best_before_date")
    surplus_expires_at = payload.get("surplus_expires_at")

    if section != Product.SECTION_DISCOUNTED and not is_surplus:
        discount_percent = 0

    if is_surplus:
        section = Product.SECTION_SURPLUS

    product = Product.objects.create(
        producer=producer,
        name=str(payload.get("name", "")).strip(),
        description=str(payload.get("description", "")).strip(),
        price=price,
        stock=stock,
        section=section,
        discount_percent=discount_percent,
        availability_mode=availability_mode,
        season_start_month=season_start_month,
        season_end_month=season_end_month,
        best_before_date=best_before_date or None,
        is_surplus=is_surplus,
        surplus_discount_percent=surplus_discount_percent,
        surplus_note=surplus_note,
        surplus_expires_at=surplus_expires_at or None,
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

    if "availability_mode" in payload:
        try:
            product.availability_mode = _coerce_availability_mode(payload["availability_mode"])
        except ValueError as exc:
            return _json_error(str(exc), 400)

    if "season_start_month" in payload:
        try:
            product.season_start_month = _coerce_month(payload["season_start_month"])
        except ValueError as exc:
            return _json_error(str(exc), 400)

    if "season_end_month" in payload:
        try:
            product.season_end_month = _coerce_month(payload["season_end_month"])
        except ValueError as exc:
            return _json_error(str(exc), 400)

    if "best_before_date" in payload:
        product.best_before_date = payload["best_before_date"] or None

    if "is_surplus" in payload:
        product.is_surplus = bool(payload["is_surplus"])

    if "surplus_discount_percent" in payload:
        try:
            product.surplus_discount_percent = _coerce_surplus_discount_percent(payload["surplus_discount_percent"])
        except ValueError as exc:
            return _json_error(str(exc), 400)

    if "surplus_note" in payload:
        product.surplus_note = str(payload["surplus_note"]).strip()

    if "surplus_expires_at" in payload:
        product.surplus_expires_at = payload["surplus_expires_at"] or None

    if product.availability_mode == Product.AVAILABILITY_SEASONAL:
        if not product.season_start_month or not product.season_end_month:
            return _json_error("Seasonal products require both season_start_month and season_end_month.", 400)
    else:
        product.season_start_month = None
        product.season_end_month = None

    if product.is_surplus:
        product.section = Product.SECTION_SURPLUS
    elif product.section != Product.SECTION_DISCOUNTED:
        product.discount_percent = 0
        product.surplus_discount_percent = 0
        product.surplus_note = ""
        product.surplus_expires_at = None

    product.save()
    return JsonResponse(_product_to_dict(product))