from django.shortcuts import get_object_or_404, redirect, render
from products.models import Product


def dashboard(request):
    query = request.GET.get("q", "").strip()

    products = Product.objects.select_related("producer").all()
    products = [product for product in products if product.is_visible_to_customers]

    if query:
        products = [
            product for product in products
            if (
                query.lower() in product.name.lower()
                or query.lower() in (product.description or "").lower()
                or query.lower() in (getattr(product.producer, "farm_name", "") or "").lower()
                or query.lower() in (getattr(product.producer, "display_name", "") or "").lower()
            )
        ]

    products = products[:4]

    return render(request, "customers/dashboard.html", {
        "products": products,
        "query": query,
    })


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

    saved = request.session.setdefault("saved_products", {})
    product_id = str(product.id)

    if product_id not in saved:
        saved[product_id] = {
            "name": product.name,
            "price": float(product.active_price if hasattr(product, "active_price") else product.price),
            "description": product.description,
            "producer": str(product.producer) if product.producer else "",
        }

    request.session.modified = True
    return redirect("customers:dashboard")


def remove_saved_product(request, product_id):
    saved = request.session.get("saved_products", {})
    product_id = str(product_id)

    if product_id in saved:
        del saved[product_id]
        request.session.modified = True

    return redirect("customers:saved_products")