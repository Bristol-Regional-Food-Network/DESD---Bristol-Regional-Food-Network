from django.shortcuts import render, get_object_or_404
from .models import Product

def product_list(request):
    q = request.GET.get("q", "").strip()
    products = Product.objects.select_related("producer").all().order_by("name")
    if q:
        products = products.filter(name__icontains=q)

    return render(request, "products/product_list.html", {"products": products, "q": q})

def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("producer"), pk=pk)
    return render(request, "products/product_detail.html", {"product": product})