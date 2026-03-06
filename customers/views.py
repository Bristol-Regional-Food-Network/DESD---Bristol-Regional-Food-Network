from django.shortcuts import render
from django.db.models import Q
from users.decorators import role_required

# Import your Product model
from products.models import Product

# @role_required("customer")
def dashboard(request):
    """
    Customer dashboard:
    - product search (read operations)
    - latest products list
    """
    q = request.GET.get("q", "").strip()

    products_qs = Product.objects.select_related("producer").all()

    if q:
        products_qs = products_qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(producer__farm_name__icontains=q)
        )

    latest_products = products_qs.order_by("-id")[:9]  # simple "latest" ordering

    context = {
        "q": q,
        "latest_products": latest_products,
    }
    return render(request, "customers/dashboard.html", context)