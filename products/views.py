from decimal import Decimal, InvalidOperation
from datetime import timedelta
import json
import math
import re
import os

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg
from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users.decorators import role_required
from .forms import ProductForm, ReviewForm
from .models import Product, Review
from producers.models import Producer
from basket.models import Order, OrderItem

from .ai_client import inspect_product_image


POSTCODE_LOOKUP = {
    "BS1": (51.4545, -2.5879),
    "BS2": (51.4590, -2.5850),
    "BS3": (51.4416, -2.6010),
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


def _postcode_area(postcode):
    if not postcode:
        return ""
    postcode = postcode.replace(" ", "").upper()
    match = re.match(r"^[A-Z]{1,2}\d{1,2}", postcode)
    return match.group(0) if match else ""


def _haversine(lat1, lon1, lat2, lon2):
    radius_miles = 3958.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return radius_miles * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def _estimate_food_miles(customer_postcode, producer):
    if not customer_postcode or not producer:
        return None

    if getattr(producer, "latitude", None) is None or getattr(producer, "longitude", None) is None:
        return None

    area = _postcode_area(customer_postcode)
    customer_coords = POSTCODE_LOOKUP.get(area)

    if not customer_coords:
        return None

    return round(
        _haversine(
            customer_coords[0],
            customer_coords[1],
            producer.latitude,
            producer.longitude,
        ),
        1,
    )


def _product_to_dict(product: Product):
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": str(product.price),
        "stock": product.stock,
        "is_organic": product.is_organic,
        "section": product.section,
        "category": product.category,
        "category_display": product.get_category_display(),
        "discount_percent": product.discount_percent,
        "discounted_price": str(product.discounted_price),
        "availability_label": product.availability_label,
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
    selected_category = request.GET.get("category", "all")
    selected_organic = request.GET.get("organic", "all")
    q = request.GET.get("q", "").strip()

    visible_products = _visible_products_queryset()

    if q:
        q_lower = q.lower()
        visible_products = [
            p for p in visible_products
            if (
                q_lower in p.name.lower()
                or q_lower in (p.description or "").lower()
                or q_lower in (getattr(p.producer, "display_name", "") or "").lower()
                or q_lower in (getattr(p.producer, "farm_name", "") or "").lower()
            )
        ]

    if selected_category != "all":
        visible_products = [p for p in visible_products if p.category == selected_category]

    if selected_organic == "certified":
        visible_products = [p for p in visible_products if p.is_organic]
    elif selected_organic == "not_certified":
        visible_products = [p for p in visible_products if not p.is_organic]

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

    categories = [
        ("all", "All Categories"),
        (Product.CATEGORY_VEGETABLES, "Vegetables"),
        (Product.CATEGORY_FRUITS, "Fruits"),
        (Product.CATEGORY_DAIRY, "Dairy Products"),
        (Product.CATEGORY_BAKERY, "Bakery Goods"),
        (Product.CATEGORY_PRESERVES, "Preserves"),
        (Product.CATEGORY_SEASONAL_SPECIALITIES, "Seasonal Specialities"),
    ]

    organic_options = [
        ("all", "All Products"),
        ("certified", "Certified Organic"),
        ("not_certified", "Not Certified"),
    ]

    saved = request.session.get("saved_products", {})
    saved_items = []

    for product_id, item in saved.items():
        saved_items.append({
            "product_id": product_id,
            "name": item.get("name", ""),
            "price": item.get("price", 0),
            "description": item.get("description", ""),
            "producer": item.get("producer", ""),
        })

    recommended_products = []

    if request.user.is_authenticated:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            rec_path = os.path.join(base_dir, "hybrid_recommendations.csv")

            if os.path.exists(rec_path):
                df = pd.read_csv(rec_path)
                user_recs = df[df["user_key"] == request.user.username].head(5)

                for _, rec in user_recs.iterrows():
                    product = Product.objects.filter(
                        name__iexact=str(rec["product_name"]).strip(),
                        producer__display_name__iexact=str(rec["producer_name"]).strip(),
                    ).select_related("producer").first()

                    if product and product.is_visible_to_customers:
                        recommended_products.append({
                            "product": product,
                            "final_score": rec.get("final_score", 0),
                            "svd_score": rec.get("svd_score", 0),
                            "rf_score": rec.get("rf_score", 0),
                            "total_orders": rec.get("total_orders", 0),
                        })

        except Exception as e:
            print("Recommendation load error:", e)

    return render(
        request,
        "products/product_list.html",
        {
            "surplus_products": surplus_products,
            "seasonal_products": seasonal_products,
            "discounted_products": discounted_products,
            "all_products": all_products,
            "categories": categories,
            "organic_options": organic_options,
            "selected_category": selected_category,
            "selected_organic": selected_organic,
            "query": q,
            "saved_items": saved_items,
            "recommended_products": recommended_products,
        },
    )


def _get_reviewable_order_for_product(user, product):
    return (
        Order.objects.filter(
            user=user,
            status=Order.STATUS_FULFILLED,
            items__product=product,
        )
        .order_by("-created_at")
        .first()
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

    postcode_param = request.GET.get("postcode", "").strip()
    if postcode_param:
        request.session["customer_postcode"] = postcode_param
        request.session.modified = True

    customer_postcode = request.session.get("customer_postcode", "")
    producer_postcode = getattr(product.producer, "postcode", "")
    food_miles = _estimate_food_miles(customer_postcode, product.producer)
    within_radius = food_miles is not None and food_miles <= 20

    reviews = product.reviews.filter(is_approved=True).select_related("customer")
    average_rating = reviews.aggregate(avg=Avg("rating"))["avg"] or 0

    can_review = False
    existing_review = None
    review_form = None

    if request.user.is_authenticated:
        existing_review = Review.objects.filter(product=product, customer=request.user).first()
        reviewable_order = _get_reviewable_order_for_product(request.user, product)
        can_review = reviewable_order is not None and existing_review is None
        if can_review:
            review_form = ReviewForm()

    return render(
        request,
        "products/product_detail.html",
        {
            "product": product,
            "customer_postcode": customer_postcode,
            "producer_postcode": producer_postcode,
            "food_miles": food_miles,
            "within_radius": within_radius,
            "reviews": reviews,
            "average_rating": average_rating,
            "can_review": can_review,
            "existing_review": existing_review,
            "review_form": review_form,
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
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.producer = producer

            if product.section != Product.SECTION_DISCOUNTED and not product.is_surplus:
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

            if product.image:
                try:
                    result = inspect_product_image(product.image.path)

                    product.ai_predicted_label = result.get("predicted_label", "")
                    product.ai_fresh_probability = result.get("fresh_probability")
                    product.ai_rotten_probability = result.get("rotten_probability")
                    product.ai_colour_score = result.get("colour_score")
                    product.ai_size_score = result.get("size_score")
                    product.ai_ripeness_score = result.get("ripeness_score")
                    product.ai_grade = result.get("grade") or ""
                    product.ai_action = result.get("action", "")
                    product.ai_explanation = "\n".join(result.get("explanation", []))
                    product.ai_last_checked_at = timezone.now()

                    product.save()

                except Exception as e:
                    messages.warning(
                        request,
                        f"Product saved, but AI inspection could not be completed: {e}"
                    )

            messages.success(request, "Product added successfully.")
            return redirect("producers:producer_dashboard")
        else:
            print("FORM ERRORS:", form.errors)
    else:
        form = ProductForm()

    return render(
        request,
        "products/add_product.html",
        {
            "form": form,
            "page_title": "Add Product",
        },
    )


@login_required
@require_http_methods(["POST"])
def submit_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    existing_review = Review.objects.filter(
        product=product,
        customer=request.user
    ).first()

    if existing_review:
        messages.error(request, "You have already reviewed this product.")
        return redirect("products:product_detail", product_id=product.id)

    reviewable_order = _get_reviewable_order_for_product(request.user, product)

    if not reviewable_order:
        messages.error(request, "You can only review products from fulfilled orders.")
        return redirect("products:product_detail", product_id=product.id)

    form = ReviewForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please correct the review form and try again.")
        return redirect("products:product_detail", product_id=product.id)

    review = form.save(commit=False)
    review.product = product
    review.customer = request.user
    review.order = reviewable_order
    review.is_verified_purchase = True
    review.save()

    messages.success(request, "Your review has been submitted successfully.")
    return redirect("products:product_detail", product_id=product.id)


@login_required
@role_required("producer")
def edit_product(request, product_id):
    producer = Producer.objects.filter(user=request.user).first()
    product = get_object_or_404(Product, id=product_id, producer=producer)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
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
            if updated_product.image:
                try:
                    result = inspect_product_image(updated_product.image.path)

                    updated_product.ai_predicted_label = result.get("predicted_label", "")
                    updated_product.ai_fresh_probability = result.get("fresh_probability")
                    updated_product.ai_rotten_probability = result.get("rotten_probability")
                    updated_product.ai_colour_score = result.get("colour_score")
                    updated_product.ai_size_score = result.get("size_score")
                    updated_product.ai_ripeness_score = result.get("ripeness_score")
                    updated_product.ai_grade = result.get("grade") or ""
                    updated_product.ai_action = result.get("action", "")
                    updated_product.ai_explanation = "\n".join(result.get("explanation", []))
                    updated_product.ai_last_checked_at = timezone.now()

                    updated_product.save()

                except Exception as e:
                    messages.warning(
                        request,
                        f"Product updated, but AI inspection could not be completed: {e}"
                    )

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
        category = request.GET.get("category")
        visible_only = request.GET.get("visible_only")
        organic = request.GET.get("organic")

        if producer_id:
            products = products.filter(producer_id=producer_id)
        if q:
            products = products.filter(
                Q(name__icontains=q)
                | Q(description__icontains=q)
                | Q(producer__display_name__icontains=q)
                | Q(producer__farm_name__icontains=q)
            ).distinct()
        if category:
            products = products.filter(category=category)
        if organic == "true":
            products = products.filter(is_organic=True)
        elif organic == "false":
            products = products.filter(is_organic=False)

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
        surplus_discount_percent = (
            _coerce_surplus_discount_percent(payload.get("surplus_discount_percent"), default=0)
            if payload.get("is_surplus")
            else 0
        )
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

    category_value = str(payload.get("category", Product.CATEGORY_VEGETABLES)).strip() or Product.CATEGORY_VEGETABLES
    if category_value not in {choice[0] for choice in Product.CATEGORY_CHOICES}:
        category_value = Product.CATEGORY_VEGETABLES

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
        is_organic=bool(payload.get("is_organic", False)),
        section=section,
        category=category_value,
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

    if "category" in payload:
        category_value = str(payload["category"]).strip()
        if category_value in {choice[0] for choice in Product.CATEGORY_CHOICES}:
            product.category = category_value

    if "is_organic" in payload:
        product.is_organic = bool(payload["is_organic"])

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