from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
import math
import re
import pgeocode

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.text import slugify
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from products.models import Product
from .forms import PaymentForm
from .models import Order, OrderItem, ProducerOrder, RecurringOrder, RecurringOrderItem


def _next_weekday(start_date, target_weekday):
    """Return the next date >= ``start_date`` that falls on ``target_weekday``."""
    days_ahead = (target_weekday - start_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return start_date + timedelta(days=days_ahead)


def _resolve_delivery_after(order_date, delivery_weekday):
    """Pick the first delivery_weekday strictly after the order_date."""
    days_ahead = (delivery_weekday - order_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return order_date + timedelta(days=days_ahead)


COMMISSION_RATE = Decimal("0.05")
PRODUCER_RATE = Decimal("0.95")


POSTCODE_LOOKUP = {
    "BS1": (51.4545, -2.5879),
    "BS2": (51.4590, -2.5850),
    "BS3": (51.4416, -2.6010),
}


def _get_basket(session):
    return session.setdefault("basket", {})


def _money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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

def _postcode_coordinates(postcode):
    if not postcode:
        return None

    nomi = pgeocode.Nominatim("GB")
    result = nomi.query_postal_code(postcode)

    if result is None:
        return None

    if result.latitude != result.latitude or result.longitude != result.longitude:
        return None

    return {
        "lat": float(result.latitude),
        "lng": float(result.longitude),
    }


def _distance_between_postcodes(customer_postcode, producer_postcode):
    customer_coords = _postcode_coordinates(customer_postcode)
    producer_coords = _postcode_coordinates(producer_postcode)

    if not customer_coords or not producer_coords:
        return None

    return round(
        _haversine(
            customer_coords["lat"],
            customer_coords["lng"],
            producer_coords["lat"],
            producer_coords["lng"],
        ),
        1,
    )

def _estimate_food_miles(customer_postcode, producer):
    if not customer_postcode or not producer:
        return None

    if producer.latitude is None or producer.longitude is None:
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
        if not producer_postcode:
            producer_user = getattr(product.producer, "user", None)
            if producer_user and hasattr(producer_user, "userprofile"):
                producer_postcode = getattr(producer_user.userprofile, "postcode", "")

        food_miles = _distance_between_postcodes(customer_postcode, producer_postcode)

        if producer_name not in groups:
            groups[producer_name] = {
                "producer_name": producer_name,
                "producer_key": slugify(producer_name),
                "producer_postcode": producer_postcode,
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
    if not customer_postcode and request.user.is_authenticated:
        customer_postcode = getattr(request.user.userprofile, "postcode", "")

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

            request.session["customer_postcode"] = cleaned["postcode"]
            request.session.modified = True

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

            # ----------------------------------------------------------------
            # TC-018: optionally save this checkout as a recurring template.
            # ----------------------------------------------------------------
            recurring_template = None
            if request.POST.get("make_recurring") == "on":
                frequency = request.POST.get("recurring_frequency", RecurringOrder.FREQ_WEEKLY)
                if frequency not in dict(RecurringOrder.FREQUENCY_CHOICES):
                    frequency = RecurringOrder.FREQ_WEEKLY

                try:
                    order_day = int(request.POST.get("recurring_order_day", 0))
                except (TypeError, ValueError):
                    order_day = 0
                try:
                    delivery_day = int(request.POST.get("recurring_delivery_day", 2))
                except (TypeError, ValueError):
                    delivery_day = 2

                order_day = max(0, min(6, order_day))
                delivery_day = max(0, min(6, delivery_day))

                today = timezone.localdate()
                next_run = _next_weekday(today, order_day)
                next_delivery = _resolve_delivery_after(next_run, delivery_day)

                recurring_template = RecurringOrder.objects.create(
                    user=request.user,
                    name=request.POST.get("recurring_name", "").strip() or "Weekly order",
                    frequency=frequency,
                    order_day=order_day,
                    delivery_day=delivery_day,
                    cardholder_name=cleaned["cardholder_name"],
                    card_last4=card_last4,
                    billing_address=cleaned["billing_address"],
                    city=cleaned["city"],
                    postcode=cleaned["postcode"],
                    country=cleaned["country"],
                    next_run_date=next_run,
                    next_delivery_date=next_delivery,
                    status=RecurringOrder.STATUS_ACTIVE,
                )

                for group in producer_groups:
                    for item in group["items"]:
                        product = Product.objects.filter(id=item["product_id"]).first()
                        RecurringOrderItem.objects.create(
                            recurring_order=recurring_template,
                            product=product,
                            producer=getattr(product, "producer", None) if product else None,
                            product_name=item["name"],
                            producer_name=item["producer"],
                            unit_display=item["unit_display"],
                            price=item["price"],
                            quantity=item["quantity"],
                        )

                messages.success(
                    request,
                    f"Recurring order saved. Your next order will be placed on "
                    f"{next_run.strftime('%A %d %b %Y')} for delivery on "
                    f"{next_delivery.strftime('%A %d %b %Y')}.",
                )

            request.session["basket"] = {}
            request.session.modified = True

            return render(request, "basket/payment_success.html", {
                "order": order,
                "subtotal": subtotal,
                "commission_amount": commission_amount,
                "grand_total": grand_total,
                "producer_groups": confirmation_groups,
                "total_food_miles": total_food_miles,
                "customer_postcode": customer_postcode,
                "recurring_template": recurring_template,
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
        "customer_postcode": customer_postcode,
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

@login_required
def basket_distance_map_api(request):
    customer_postcode = request.GET.get("customer_postcode", "").strip()
    producer_postcode = request.GET.get("producer_postcode", "").strip()

    customer_coords = _postcode_coordinates(customer_postcode)
    producer_coords = _postcode_coordinates(producer_postcode)

    if not customer_coords or not producer_coords:
        return JsonResponse({
            "success": False,
            "message": "Map could not be calculated."
        })

    distance_miles = round(
        _haversine(
            customer_coords["lat"],
            customer_coords["lng"],
            producer_coords["lat"],
            producer_coords["lng"],
        ),
        1,
    )

    return JsonResponse({
        "success": True,
        "customer_postcode": customer_postcode,
        "producer_postcode": producer_postcode,
        "customer": customer_coords,
        "producer": producer_coords,
        "distance_miles": distance_miles,
    })


# ---------------------------------------------------------------------------
# TC-018: Recurring orders management
# ---------------------------------------------------------------------------
@login_required
def recurring_orders_list(request):
    """List page for the customer's recurring order templates."""
    templates = (
        RecurringOrder.objects
        .filter(user=request.user)
        .prefetch_related("items")
        .order_by("-created_at")
    )

    enriched = []
    for template in templates:
        items = list(template.items.all())

        # Detect any unavailable products to surface a warning to the restaurant.
        unavailable = []
        for item in items:
            product = item.product
            if not product or not product.is_visible_to_customers or product.stock <= 0:
                unavailable.append(item.product_name)

        enriched.append({
            "template": template,
            "items": items,
            "template_total": template.template_total,
            "unavailable_items": unavailable,
        })

    return render(request, "basket/recurring_orders_list.html", {
        "templates": enriched,
    })


@login_required
def recurring_order_detail(request, recurring_id):
    template = get_object_or_404(
        RecurringOrder.objects.prefetch_related("items__product__producer"),
        id=recurring_id,
        user=request.user,
    )

    items = list(template.items.all())

    # Group items by producer so the restaurant can see who supplies what.
    producer_groups = {}
    for item in items:
        key = item.producer_name or "Unknown Producer"
        producer_groups.setdefault(key, []).append(item)

    unavailable_items = []
    for item in items:
        product = item.product
        if not product or not product.is_visible_to_customers or product.stock <= 0:
            unavailable_items.append(item.product_name)

    return render(request, "basket/recurring_order_detail.html", {
        "template": template,
        "items": items,
        "producer_groups": producer_groups,
        "unavailable_items": unavailable_items,
    })


@login_required
@require_POST
def recurring_order_pause(request, recurring_id):
    template = get_object_or_404(
        RecurringOrder, id=recurring_id, user=request.user
    )

    if template.status == RecurringOrder.STATUS_ACTIVE:
        template.status = RecurringOrder.STATUS_PAUSED
        template.save(update_fields=["status", "updated_at"])
        messages.success(request, "Recurring order paused. No further orders will be generated until resumed.")
    elif template.status == RecurringOrder.STATUS_PAUSED:
        template.status = RecurringOrder.STATUS_ACTIVE
        template.save(update_fields=["status", "updated_at"])
        messages.success(request, "Recurring order resumed.")
    else:
        messages.error(request, "Cancelled recurring orders cannot be resumed.")

    return redirect("basket:recurring_order_detail", recurring_id=template.id)


@login_required
@require_POST
def recurring_order_cancel(request, recurring_id):
    template = get_object_or_404(
        RecurringOrder, id=recurring_id, user=request.user
    )
    template.status = RecurringOrder.STATUS_CANCELLED
    template.save(update_fields=["status", "updated_at"])
    messages.success(request, "Recurring order cancelled.")
    return redirect("basket:recurring_orders_list")


@login_required
def recurring_order_modify_next(request, recurring_id):
    """
    Per the acceptance criteria, modifications can be applied either to the
    next instance only (so the template stays untouched) or to the template
    itself going forward.
    """
    template = get_object_or_404(
        RecurringOrder.objects.prefetch_related("items"),
        id=recurring_id,
        user=request.user,
    )

    if request.method == "POST":
        scope = request.POST.get("scope", "next_only")

        for item in template.items.all():
            field_name = f"quantity_{item.id}"
            raw_value = request.POST.get(field_name)
            if raw_value in (None, ""):
                continue
            try:
                new_quantity = int(raw_value)
            except (TypeError, ValueError):
                continue
            new_quantity = max(0, new_quantity)

            if scope == "template":
                # Apply permanently; clear per-instance override.
                item.quantity = new_quantity
                item.next_quantity_override = None
                item.save(update_fields=["quantity", "next_quantity_override"])
            else:
                # Apply only to the next generated order.
                if new_quantity == item.quantity:
                    item.next_quantity_override = None
                else:
                    item.next_quantity_override = new_quantity
                item.save(update_fields=["next_quantity_override"])

        if scope == "template":
            messages.success(request, "Recurring template updated. Future orders will use the new quantities.")
        else:
            messages.success(request, "Next scheduled order updated. The template is unchanged.")

        return redirect("basket:recurring_order_detail", recurring_id=template.id)

    return render(request, "basket/recurring_order_modify.html", {
        "template": template,
        "items": list(template.items.all()),
    })