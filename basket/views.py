from decimal import Decimal
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from products.models import Product
from .forms import PaymentForm
from .models import Order, OrderItem


def _get_basket(session):
    return session.setdefault("basket", {})


def basket_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if not product.is_visible_to_customers:
        messages.error(request, "This product is currently not available to order.")
        return redirect("products:product_list")

    basket = _get_basket(request.session)

    product_id = str(product.id)
    quantity = int(request.POST.get("quantity", 1))

    if quantity < 1:
        quantity = 1

    if quantity > product.stock:
        quantity = product.stock

    if product_id in basket:
        basket[product_id]["quantity"] += quantity
        if basket[product_id]["quantity"] > product.stock:
            basket[product_id]["quantity"] = product.stock
    else:
        basket[product_id] = {
            "name": product.name,
            "price": float(product.active_price),
            "quantity": quantity,
        }

    request.session.modified = True
    return redirect("products:product_detail", product_id=product.id)


def basket_update(request, product_id):
    basket = _get_basket(request.session)
    product_id = str(product_id)

    if product_id in basket:
        action = request.POST.get("action")
        product = Product.objects.filter(id=product_id).first()

        if not product or not product.is_visible_to_customers:
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
    remove_ids = []

    for product_id, item in basket.items():
        product = Product.objects.filter(id=product_id).first()

        if not product or not product.is_visible_to_customers:
            remove_ids.append(product_id)
            continue

        quantity = min(int(item["quantity"]), product.stock)
        price = Decimal(str(product.active_price))
        subtotal = price * quantity
        total += subtotal

        items.append({
            "product_id": product_id,
            "name": product.name,
            "price": price,
            "quantity": quantity,
            "subtotal": subtotal,
        })

        basket[product_id]["price"] = float(product.active_price)

    for product_id in remove_ids:
        del basket[product_id]

    if remove_ids:
        request.session.modified = True

    return render(request, "basket/basket_detail.html", {
        "basket_items": items,
        "basket_total": total,
    })


def checkout(request):
    basket = request.session.get("basket", {})
    items = []
    total = Decimal("0.00")

    for product_id, item in list(basket.items()):
        product = Product.objects.filter(id=product_id).first()

        if not product or not product.is_visible_to_customers:
            continue

        quantity = min(int(item["quantity"]), product.stock)
        price = Decimal(str(product.active_price))
        subtotal = price * quantity
        total += subtotal

        items.append({
            "product_id": product_id,
            "name": product.name,
            "price": price,
            "quantity": quantity,
            "subtotal": subtotal,
        })

    if not basket or not items:
        messages.warning(request, "There are no available products in your basket.")
        return redirect("basket:basket_detail")

    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            card_number = cleaned["card_number"]
            card_last4 = card_number[-4:]

            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                cardholder_name=cleaned["cardholder_name"],
                card_last4=card_last4,
                billing_address=cleaned["billing_address"],
                city=cleaned["city"],
                postcode=cleaned["postcode"],
                country=cleaned["country"],
                total_amount=total,
                status="paid",
            )

            for item in items:
                product = Product.objects.filter(id=item["product_id"]).first()

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=item["name"],
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

            request.session["basket"] = {}
            request.session.modified = True

            return render(request, "basket/payment_success.html", {
                "basket_total": total,
                "order": order,
            })
    else:
        form = PaymentForm()

    return render(request, "basket/checkout.html", {
        "basket_items": items,
        "basket_total": total,
        "form": form,
    })