from django.shortcuts import get_object_or_404, redirect, render
from products.models import Product


def dashboard(request):
    return redirect("products:product_list")


def saved_products(request):
    saved = request.session.get("saved_products", {})
    items = []

    for product_id, item in saved.items():
        items.append({
            "product_id": product_id,
            "name": item["name"],
            "price": item["price"],
            "description": item["description"],
            "producer": item["producer"],
        })

    return render(request, "customers/saved_products.html", {
        "saved_items": items,
    })


def save_product(request, product_id):
    product = get_object_or_404(Product.objects.select_related("producer"), id=product_id)

    if not product.is_visible_to_customers:
        return redirect("products:product_list")

    saved = request.session.get("saved_products", {})
    product_key = str(product.id)

    if product_key not in saved:
        saved[product_key] = {
            "name": product.name,
            "price": float(product.active_price if hasattr(product, "active_price") else product.price),
            "description": product.description,
            "producer": str(product.producer) if product.producer else "",
        }

    request.session["saved_products"] = saved
    request.session.modified = True

    return redirect("products:product_list")


def remove_saved_product(request, product_id):
    saved = request.session.get("saved_products", {})
    product_key = str(product_id)

    if product_key in saved:
        del saved[product_key]
        request.session["saved_products"] = saved
        request.session.modified = True

    return redirect("products:product_list")