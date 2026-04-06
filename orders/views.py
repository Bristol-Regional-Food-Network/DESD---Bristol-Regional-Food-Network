from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Order


@login_required
def order_history(request):
    orders = (
        Order.objects.filter(customer=request.user)
        .prefetch_related("items__product__producer")
        .order_by("-order_date")
    )

    producer_filter = request.GET.get("producer", "").strip().lower()
    date_filter = request.GET.get("date", "").strip()

    filtered_orders = list(orders)

    if producer_filter:
        filtered_orders = [
            order for order in filtered_orders
            if any(
                producer_filter in item.product.producer.display_name.lower()
                for item in order.items.all()
            )
        ]

    if date_filter:
        filtered_orders = [
            order for order in filtered_orders
            if order.order_date.strftime("%Y-%m-%d") == date_filter
        ]

    return render(
        request,
        "orders/order_history.html",
        {
            "orders": filtered_orders,
            "producer_filter": request.GET.get("producer", ""),
            "date_filter": date_filter,
        },
    )


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product__producer"),
        id=order_id,
        customer=request.user,
    )

    masked_payment = "Not available"
    if order.payment_reference:
        last_four = order.payment_reference[-4:]
        masked_payment = f"**** **** **** {last_four}"

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
            "masked_payment": masked_payment,
        },
    )


@login_required
def reorder_order(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"),
        id=order_id,
        customer=request.user,
    )

    basket = request.session.get("basket", {})
    unavailable_items = []

    for item in order.items.all():
        product = item.product

        if not product.is_visible_to_customers or product.stock < item.quantity:
            unavailable_items.append(product.name)
            continue

        product_id = str(product.id)
        current_qty = basket.get(product_id, 0)
        basket[product_id] = current_qty + item.quantity

    request.session["basket"] = basket
    request.session.modified = True

    if unavailable_items:
        messages.warning(
            request,
            "Some items were unavailable and were not added: " + ", ".join(unavailable_items)
        )

    messages.success(request, "Available items from this order were added to your basket.")
    return redirect("basket:basket_detail")