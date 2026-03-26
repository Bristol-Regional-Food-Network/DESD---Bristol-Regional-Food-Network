from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
import math
import re

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.text import slugify

from products.models import Product
from .forms import PaymentForm
from .models import Order, OrderItem, ProducerOrder


COMMISSION_RATE = Decimal("0.05")
PRODUCER_RATE = Decimal("0.95")

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


def _get_basket(session):
    return session.setdefault("basket", {})


def _money(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _normalise_postcode(postcode):
    if not postcode:
        return ""
    return re.sub(r"\s+", "", str(postcode).upper())


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

    return round(
        _haversine_miles(
            customer_coords[0],
            customer_coords[1],
            producer_coords[0],
            producer_coords[1],
        ),
        1,
    )


def _build_checkout_groups(basket, customer_postcode=""):
    groups = {}
    total = Decimal("0.00")
    total_food_miles = 0.0

    for product_id, item in basket.items():
        price = Decimal(str(item["price"]))
        quantity = int(item["quantity"])
        subtotal = _money(price * quantity)
        producer_name = item.get("producer", "Unknown Producer")
        producer_postcode = item.get("producer_postcode", "")
        food_miles = _estimate_food_miles(customer_postcode, producer_postcode)

        if producer_name not in groups:
            groups[producer_name] = {
                "producer_name": producer_name,
                "producer_key": slugify(producer_name),
                "items": [],
                "subtotal": Decimal("0.00"),
                "payout_amount": Decimal("0.00"),
                "food_miles_total": 0.0,
            }

        groups[producer_name]["items"].append({
            "product_id": product_id,
            "name": item["name"],
            "producer": producer_name,
            "unit_display": item.get("unit_display", "each"),
            "price": price,
            "quantity": quantity,
            "subtotal": subtotal,
            "food_miles": food_miles,
        })
        groups[producer_name]["subtotal"] += subtotal
        total += subtotal

        if food_miles is not None:
            groups[producer_name]["food_miles_total"] += food_miles * quantity
            total_food_miles += food_miles * quantity

    for group in groups.values():
        group["subtotal"] = _money(group["subtotal"])
        group["payout_amount"] = _money(group["subtotal"] * PRODUCER_RATE)
        group["food_miles_total"] = round(group["food_miles_total"], 1)

    return list(groups.values()), _money(total), round(total_food_miles, 1)


def _validate_producer_delivery_dates(request, producer_groups):
    errors = {}
    selected_dates = {}
    min_date = timezone.localdate() + timedelta(days=2)

    for group in producer_groups:
        field_name = f"delivery_date_{group['producer_key']}"
        raw_value = request.POST.get(field_name, "").strip()

        if not raw_value:
            errors[field_name] = "Delivery date is required."
            continue

        try:
            parsed_date = datetime.strptime(raw_value, "%Y-%m-%d").date()
        except ValueError:
            errors[field_name] = "Enter a valid delivery date."
            continue

        if parsed_date < min_date:
            errors[field_name] = "Delivery date must be at least 48 hours from today."
            continue

        selected_dates[group["producer_key"]] = parsed_date

    return selected_dates, errors, min_date


@login_required
def basket_add(request, product_id):
    product = get_object_or_404(Product.objects.select_related("producer"), id=product_id)
    basket = _get_basket(request.session)

    product_id = str(product.id)
    quantity = request.POST.get("quantity")

    try:
        quantity = int(quantity)
        if quantity < 1:
            quantity = 1
    except (TypeError, ValueError):
        quantity = 1

    if product_id in basket:
        basket[product_id]["quantity"] += quantity
    else:
        basket[product_id] = {
            "name": product.name,
            "price": float(product.price),
            "quantity": quantity,
            "producer": product.producer.display_name,
            "producer_postcode": getattr(product.producer, "postcode", ""),
            "unit_display": product.unit_display,
        }

    request.session.modified = True
    messages.success(request, f"{product.name} added to basket.")
    return redirect("products:product_detail", product_id=product.id)


@login_required
def basket_update(request, product_id):
    basket = _get_basket(request.session)
    product_id = str(product_id)

    if product_id in basket:
        action = request.POST.get("action")

        if action == "increase":
            basket[product_id]["quantity"] += 1
        elif action == "decrease":
            basket[product_id]["quantity"] -= 1

            if basket[product_id]["quantity"] <= 0:
                del basket[product_id]

        request.session.modified = True

    return redirect("basket:basket_detail")


@login_required
def basket_remove(request, product_id):
    basket = _get_basket(request.session)
    product_id = str(product_id)

    if product_id in basket:
        del basket[product_id]
        request.session.modified = True

    return redirect("basket:basket_detail")


@login_required
def basket_detail(request):
    if request.method == "POST":
        postcode = request.POST.get("customer_postcode", "").strip()
        request.session["customer_postcode"] = postcode
        request.session.modified = True
        return redirect("basket:basket_detail")

    basket = _get_basket(request.session)
    customer_postcode = request.session.get("customer_postcode", "")
    producer_groups, total, total_food_miles = _build_checkout_groups(basket, customer_postcode)

    return render(request, "basket/basket_detail.html", {
        "producer_groups": producer_groups,
        "basket_total": total,
        "basket_items": basket,
        "customer_postcode": customer_postcode,
        "total_food_miles": total_food_miles,
    })


@login_required
def checkout(request):
    basket = request.session.get("basket", {})

    if not basket:
        messages.warning(request, "Your basket is empty.")
        return redirect("basket:basket_detail")

    customer_postcode = request.session.get("customer_postcode", "")
    producer_groups, subtotal, total_food_miles = _build_checkout_groups(basket, customer_postcode)
    commission_amount = _money(subtotal * COMMISSION_RATE)
    total_producer_amount = _money(subtotal * PRODUCER_RATE)
    grand_total = _money(subtotal + commission_amount)

    initial_data = {}
    full_name = f"{request.user.first_name} {request.user.last_name}".strip()
    if full_name:
        initial_data["cardholder_name"] = full_name

    producer_delivery_dates = {}
    delivery_date_errors = {}
    min_delivery_date = timezone.localdate() + timedelta(days=2)

    if request.method == "POST":
        form = PaymentForm(request.POST)
        producer_delivery_dates, delivery_date_errors, min_delivery_date = _validate_producer_delivery_dates(
            request, producer_groups
        )

        if form.is_valid() and not delivery_date_errors:
            cleaned = form.cleaned_data
            card_last4 = cleaned["card_number"][-4:]
            payment_reference = f"TEST-{uuid4().hex[:12].upper()}"

            parent_delivery_date = min(producer_delivery_dates.values()) if producer_delivery_dates else min_delivery_date
            order_producer_name = (
                producer_groups[0]["producer_name"]
                if len(producer_groups) == 1
                else "Multiple Producers"
            )

            order = Order.objects.create(
                user=request.user,
                producer_name=order_producer_name,
                cardholder_name=cleaned["cardholder_name"],
                card_last4=card_last4,
                billing_address=cleaned["billing_address"],
                city=cleaned["city"],
                postcode=cleaned["postcode"],
                country=cleaned["country"],
                delivery_date=parent_delivery_date,
                payment_reference=payment_reference,
                total_amount=grand_total,
                commission_amount=commission_amount,
                producer_amount=total_producer_amount,
                status=Order.STATUS_PENDING,
            )

            confirmation_groups = []

            for group in producer_groups:
                producer_order = ProducerOrder.objects.create(
                    order=order,
                    producer_name=group["producer_name"],
                    delivery_date=producer_delivery_dates[group["producer_key"]],
                    subtotal_amount=group["subtotal"],
                    payout_amount=group["payout_amount"],
                    status=ProducerOrder.STATUS_PENDING,
                )

                for item in group["items"]:
                    product = Product.objects.filter(id=item["product_id"]).first()

                    OrderItem.objects.create(
                        order=order,
                        producer_order=producer_order,
                        product=product,
                        product_name=item["name"],
                        producer_name=item["producer"],
                        unit_display=item["unit_display"],
                        price=item["price"],
                        quantity=item["quantity"],
                    )

                confirmation_groups.append({
                    "producer_name": producer_order.producer_name,
                    "delivery_date": producer_order.delivery_date,
                    "subtotal": producer_order.subtotal_amount,
                    "payout_amount": producer_order.payout_amount,
                    "items": group["items"],
                })

            request.session["basket"] = {}
            request.session.modified = True

            return render(request, "basket/payment_success.html", {
                "order": order,
                "subtotal": subtotal,
                "commission_amount": commission_amount,
                "grand_total": grand_total,
                "producer_groups": confirmation_groups,
                "total_food_miles": total_food_miles,
            })
    else:
        form = PaymentForm(initial=initial_data)

    return render(request, "basket/checkout.html", {
        "producer_groups": producer_groups,
        "subtotal": subtotal,
        "commission_amount": commission_amount,
        "producer_amount": total_producer_amount,
        "grand_total": grand_total,
        "form": form,
        "min_delivery_date": min_delivery_date.isoformat(),
        "delivery_date_errors": delivery_date_errors,
        "submitted_delivery_dates": producer_delivery_dates,
        "total_food_miles": total_food_miles,
    })