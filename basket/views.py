from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from products.models import Product
from .forms import PaymentForm
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

    if product_id in basket:
        basket[product_id]["quantity"] += quantity
    else:
        basket[product_id] = {
            "name": product.name,
            "price": float(product.price),
            "quantity": quantity,
        }

    request.session.modified = True
    return redirect("products:product_detail", product_id=product.id)


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
        price = Decimal(str(item["price"]))
        quantity = int(item["quantity"])
        subtotal = price * quantity
        total += subtotal

        items.append({
            "product_id": product_id,
            "name": item["name"],
            "price": price,
            "quantity": quantity,
            "subtotal": subtotal,
        })

    return render(request, "basket/basket_detail.html", {
        "basket_items": items,
        "basket_total": total,
    })


def checkout(request):
    basket = request.session.get("basket", {})
    items = []
    total = Decimal("0.00")

    for product_id, item in basket.items():
        price = Decimal(str(item["price"]))
        quantity = int(item["quantity"])
        subtotal = price * quantity
        total += subtotal

        items.append({
            "product_id": product_id,
            "name": item["name"],
            "price": price,
            "quantity": quantity,
            "subtotal": subtotal,
        })

    if not basket:
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