from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from products.models import Product
from producers.models import Producer
from .models import Order, OrderItem


def _get_basket(session):
    return session.setdefault("basket", {})


def basket_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    basket = _get_basket(request.session)

    product_id = str(product.id)
    quantity = int(request.POST.get("quantity", 1))

    if quantity < 1:
        quantity = 1

    current_qty = basket.get(product_id, {}).get("quantity", 0)
    new_qty = current_qty + quantity

    if new_qty > product.stock:
        messages.error(request, f"Only {product.stock} of {product.name} available.")
        return redirect("products:product_detail", product_id=product.id)

    if product_id in basket:
        basket[product_id]["quantity"] = new_qty
    else:
        basket[product_id] = {
            "name": product.name,
            "price": float(product.price),
            "quantity": quantity,
        }

    request.session.modified = True
    messages.success(request, f"{product.name} added to basket.")
    return redirect("products:product_detail", product_id=product.id)


def basket_update(request, product_id):
    basket = _get_basket(request.session)
    product_id = str(product_id)

    if product_id in basket:
        action = request.POST.get("action")
        product = get_object_or_404(Product, id=product_id)

        if action == "increase":
            if basket[product_id]["quantity"] < product.stock:
                basket[product_id]["quantity"] += 1
            else:
                messages.error(request, f"No more stock available for {product.name}.")
        elif action == "decrease":
            basket[product_id]["quantity"] -= 1
            if basket[product_id]["quantity"] <= 0:
                del basket[product_id]

        request.session.modified = True

    return redirect("basket:basket_detail")


def basket_remove(request, product_id):
    basket = _get_basket(request.session)
    product_id = str(product_id)

    if product_id in basket:
        del basket[product_id]
        request.session.modified = True

    return redirect("basket:basket_detail")


def basket_detail(request):
    basket = _get_basket(request.session)

    items = []
    total = Decimal("0.00")

    for product_id, item in basket.items():
        subtotal = Decimal(str(item["price"])) * item["quantity"]
        total += subtotal
        items.append({
            "product_id": product_id,
            "name": item["name"],
            "price": item["price"],
            "quantity": item["quantity"],
            "subtotal": subtotal,
        })

    return render(request, "basket/basket_detail.html", {
        "basket_items": items,
        "basket_total": total,
    })


@login_required
@transaction.atomic
def checkout(request):
    basket = request.session.get("basket", {})

    if not basket:
        messages.error(request, "Your basket is empty.")
        return redirect("basket:basket_detail")

    items = []
    total = Decimal("0.00")

    product_rows = []

    for product_id, item in basket.items():
        product = get_object_or_404(Product, id=product_id)

        quantity = int(item["quantity"])
        price = Decimal(str(item["price"]))
        subtotal = price * quantity

        if quantity > product.stock:
            messages.error(request, f"Not enough stock for {product.name}.")
            return redirect("basket:basket_detail")

        total += subtotal
        product_rows.append((product, quantity, price))

        items.append({
            "product_id": product.id,
            "name": product.name,
            "price": price,
            "quantity": quantity,
            "subtotal": subtotal,
        })

    if request.method == "POST":
        order = Order.objects.create(
            customer=request.user,
            total_amount=total,
            status="paid",
        )

        for product, quantity, price in product_rows:
            OrderItem.objects.create(
                order=order,
                product=product,
                producer=product.producer,
                quantity=quantity,
                unit_price=price,
                fulfilment_status="pending",
            )
            product.stock -= quantity
            product.save()

        request.session["basket"] = {}
        request.session.modified = True

        return render(request, "basket/payment_success.html", {
            "basket_total": total,
            "order": order,
        })

    return render(request, "basket/checkout.html", {
        "basket_items": items,
        "basket_total": total,
    })


@login_required
def order_history(request):
    orders = Order.objects.filter(customer=request.user).order_by("-created_at")
    return render(request, "basket/order_history.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    return render(request, "basket/order_detail.html", {"order": order})


@login_required
@transaction.atomic
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)

    if order.status != "paid":
        messages.error(request, "Only paid orders can be cancelled.")
        return redirect("basket:order_detail", order_id=order.id)

    if order.items.filter(fulfilment_status="fulfilled").exists():
        messages.error(request, "This order can no longer be cancelled because at least one item has already been fulfilled.")
        return redirect("basket:order_detail", order_id=order.id)

    order.status = "cancelled"
    order.save()

    for item in order.items.all():
        item.fulfilment_status = "cancelled"
        item.save(update_fields=["fulfilment_status"])
        item.product.stock += item.quantity
        item.product.save()

    messages.success(request, f"Order #{order.id} cancelled successfully.")
    return redirect("basket:order_detail", order_id=order.id)