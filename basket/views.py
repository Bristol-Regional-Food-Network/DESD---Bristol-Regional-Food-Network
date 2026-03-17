from django.shortcuts import get_object_or_404, redirect, render
from products.models import Product
from .models import Order


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
    total = 0

    for product_id, item in basket.items():
        subtotal = item["price"] * item["quantity"]
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
def checkout(request):
    basket = request.session.get("basket", {})

    items = []
    total = 0

    for product_id, item in basket.items():
        subtotal = item["price"] * item["quantity"]
        total += subtotal

        items.append({
            "name": item["name"],
            "price": item["price"],
            "quantity": item["quantity"],
            "subtotal": subtotal,
        })
    if request.method == "POST":
        # Create an Order record for authenticated users so management can track purchases
        if request.user.is_authenticated:
            # build a simple text summary of items
            lines = []
            for it in items:
                lines.append(f"{it['quantity']} x {it['name']} @ {it['price']}")

            notes = "\n".join(lines)

            Order.objects.create(
                customer=request.user,
                total_amount=total,
                status="paid",
                notes=notes,
            )

        request.session["basket"] = {}
        request.session.modified = True

        return render(request, "basket/payment_success.html", {
            "basket_total": total,
        })

    return render(request, "basket/checkout.html", {
        "basket_items": items,
        "basket_total": total,
    })