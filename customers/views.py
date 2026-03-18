from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q
from products.models import Product


def dashboard(request):
    query = request.GET.get("q", "").strip()

    products = Product.objects.select_related("producer").all()

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(producer__farm_name__icontains=query)
        ).distinct()
    else:
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
    product = get_object_or_404(Product, id=product_id)
    saved = request.session.setdefault("saved_products", {})

    product_id = str(product.id)

    if product_id not in saved:
        saved[product_id] = {
            "name": product.name,
            "price": float(product.price),
            "description": product.description,
            "producer": str(product.producer) if product.producer else "",
        }

    request.session.modified = True
    return redirect("customer_dashboard")


def remove_saved_product(request, product_id):
    saved = request.session.get("saved_products", {})
    product_id = str(product_id)

    if product_id in saved:
        del saved[product_id]
        request.session.modified = True

    return redirect("saved_products")