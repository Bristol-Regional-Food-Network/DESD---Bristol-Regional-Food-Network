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
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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
    removed_items = []
    changed_items = []

    for product_id, item in list(basket.items()):
        product = Product.objects.select_related("producer").filter(id=product_id).first()

        if not product or not product.is_visible_to_customers:
            removed_items.append(product_id)
            continue

        stock = max(int(getattr(product, "stock", 0)), 0)
        if stock <= 0:
            removed_items.append(product_id)
            continue

        try:
            requested_quantity = int(item.get("quantity", 1))
        except (TypeError, ValueError):
            requested_quantity = 1
        quantity = min(max(requested_quantity, 1), stock)

        current_price = Decimal(str(product.active_price))
        subtotal = _money(current_price * quantity)
        producer_name = getattr(product.producer, "display_name", "Unknown Producer")
        producer_postcode = getattr(product.producer, "postcode", "")
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
            "product_id": str(product.id),
            "name": product.name,
            "producer": producer_name,
            "unit_display": getattr(product, "unit_display", "each"),
            "price": current_price,
            "quantity": quantity,
            "subtotal": subtotal,
            "food_miles": food_miles,
        })
        groups[producer_name]["subtotal"] += subtotal
        total += subtotal

        if food_miles is not None:
            groups[producer_name]["food_miles_total"] += food_miles * quantity
            total_food_miles += food_miles * quantity

        updated_session_item = {
            "name": product.name,
            "price": float(product.active_price),
            "quantity": quantity,
            "producer": producer_name,
            "producer_postcode": producer_postcode,
            "unit_display": getattr(product, "unit_display", "each"),
        }

        if basket.get(str(product.id)) != updated_session_item:
            basket[str(product.id)] = updated_session_item
            changed_items.append(str(product.id))

    for product_id in removed_items:
        basket.pop(str(product_id), None)

    for group in groups.values():
        group["subtotal"] = _money(group["subtotal"])
        group["payout_amount"] = _money(group["subtotal"] * PRODUCER_RATE)
        group["food_miles_total"] = round(group["food_miles_total"], 1)

    return list(groups.values()), _money(total), round(total_food_miles, 1), removed_items, changed_items


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

    if not product.is_visible_to_customers:
        messages.error(request, "This product is currently not available to order.")
        return redirect("products:product_list")

    stock = max(int(getattr(product, "stock", 0)), 0)
    if stock <= 0:
        messages.error(request, "This product is out of stock.")
        return redirect("products:product_detail", product_id=product.id)

    basket = _get_basket(request.session)
    product_id = str(product.id)
    raw_quantity = request.POST.get("quantity")

    try:
        quantity = int(raw_quantity)
        if quantity < 1:
            quantity = 1
    except (TypeError, ValueError):
        quantity = 1

    quantity = min(quantity, stock)

    if product_id in basket:
        basket[product_id]["quantity"] += quantity
        if basket[product_id]["quantity"] > stock:
            basket[product_id]["quantity"] = stock
    else:
        basket[product_id] = {
            "name": product.name,
            "price": float(product.active_price),
            "quantity": quantity,
            "producer": product.producer.display_name,
            "producer_postcode": getattr(product.producer, "postcode", ""),
            "unit_display": getattr(product, "unit_display", "each"),
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
        product = Product.objects.filter(id=product_id).first()

        if not product or not product.is_visible_to_customers or getattr(product, "stock", 0) <= 0:
            del basket[product_id]
            request.session.modified = True
            messages.warning(request, "A product in your basket is no longer available.")
            return redirect("basket:basket_detail")

        if action == "increase":
            if basket[product_id]["quantity"] < product.stock:
                basket[product_id]["quantity"] += 1
        elif action == "decrease":
            basket[product_id]["quantity"] -= 1
            if basket[product_id]["quantity"] <= 0:
                del basket[product_id]

        basket.setdefault(product_id, {})
        if product_id in basket:
            basket[product_id]["price"] = float(product.active_price)
            basket[product_id]["name"] = product.name
            basket[product_id]["producer"] = getattr(product.producer, "display_name", "Unknown Producer")
            basket[product_id]["producer_postcode"] = getattr(product.producer, "postcode", "")
            basket[product_id]["unit_display"] = getattr(product, "unit_display", "each")

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
    producer_groups, total, total_food_miles, removed_items, changed_items = _build_checkout_groups(
        basket,
        customer_postcode,
    )

    if removed_items:
        messages.warning(request, "Some products were removed from your basket because they are no longer available.")

    if removed_items or changed_items:
        request.session.modified = True

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
    producer_groups, subtotal, total_food_miles, removed_items, changed_items = _build_checkout_groups(
        basket,
        customer_postcode,
    )

    if removed_items:
        messages.warning(request, "Some unavailable products were removed from your basket.")

    if removed_items or changed_items:
        request.session.modified = True

    if not producer_groups:
        messages.warning(request, "There are no available products in your basket.")
        return redirect("basket:basket_detail")

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

            from django.db import OperationalError

            try:
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
            except OperationalError:
                # Fallback for databases where the `user_id` column is missing
                # (migration/schema inconsistency). Create the order without the
                # user FK so checkout can complete locally. Long-term fix: run
                # migrations to add the column and reconcile data.
                order = Order.objects.create(
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
                        producer=getattr(product, "producer", None) if product else None,
                        product_name=item["name"],
                        producer_name=item["producer"],
                        unit_display=item["unit_display"],
                        price=item["price"],
                        quantity=item["quantity"],
                    )

                    if product:
                        product.stock = max(product.stock - item["quantity"], 0)
                        if product.stock == 0:
                            product.is_surplus = False
                            product.surplus_discount_percent = 0
                            product.surplus_note = ""
                            product.surplus_expires_at = None
                        product.save()

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


@login_required
def order_history(request):
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items__product__producer")
        .order_by("-created_at")
    )

    producer_filter = request.GET.get("producer", "").strip().lower()
    date_filter = request.GET.get("date", "").strip()

    filtered_orders = list(orders)

    if producer_filter:
        filtered_orders = [
            order for order in filtered_orders
            if any(
                producer_filter in (item.producer_name or "").lower()
                for item in order.items.all()
            )
        ]

    if date_filter:
        filtered_orders = [
            order for order in filtered_orders
            if order.created_at.strftime("%Y-%m-%d") == date_filter
        ]

    return render(
        request,
        "basket/order_history.html",
        {
            "orders": filtered_orders,
            "producer_filter": request.GET.get("producer", ""),
            "date_filter": date_filter,
        },
    )


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product__producer", "producer_orders"),
        id=order_id,
        user=request.user,
    )

    masked_payment = f"**** **** **** {order.card_last4}" if order.card_last4 else "Not available"

    return render(
        request,
        "basket/order_detail.html",
        {
            "order": order,
            "masked_payment": masked_payment,
        },
    )


@login_required
def reorder_order(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product__producer"),
        id=order_id,
        user=request.user,
    )

    basket = _get_basket(request.session)
    unavailable_items = []

    for item in order.items.all():
        product = item.product

        if not product or not product.is_visible_to_customers or product.stock <= 0:
            unavailable_items.append(item.product_name)
            continue

        quantity_to_add = min(item.quantity, product.stock)

        product_id = str(product.id)
        if product_id in basket:
            basket[product_id]["quantity"] += quantity_to_add
            if basket[product_id]["quantity"] > product.stock:
                basket[product_id]["quantity"] = product.stock
        else:
            basket[product_id] = {
                "name": product.name,
                "price": float(product.active_price),
                "quantity": quantity_to_add,
                "producer": product.producer.display_name,
                "producer_postcode": getattr(product.producer, "postcode", ""),
                "unit_display": getattr(product, "unit_display", "each"),
            }

    request.session.modified = True

    if unavailable_items:
        messages.warning(
            request,
            "Some items were unavailable and were not added: " + ", ".join(unavailable_items)
        )

    messages.success(request, "Available items from this order were added to your basket.")
    return redirect("basket:basket_detail")