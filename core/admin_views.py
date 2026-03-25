from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User
from django.urls import reverse

from producers.models import Producer
from basket.models import Order
from .forms import UserForm, ProducerForm, OrderForm


def _require_admin(user):
    try:
        return user.userprofile.role == "admin"
    except Exception:
        return False


def admin_dashboard(request):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Forbidden")
    total_users = User.objects.count()
    total_producers = Producer.objects.count()
    total_orders = Order.objects.count()
    recent_orders = Order.objects.select_related("customer").order_by("-created_at")[:5]

    return render(request, "admin/dashboard.html", {
        "total_users": total_users,
        "total_producers": total_producers,
        "total_orders": total_orders,
        "recent_orders": recent_orders,
    })


@login_required
def customers_list(request):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Forbidden")
    customers = User.objects.filter(is_active=True).order_by("username")
    return render(request, "admin/customers_list.html", {"customers": customers})


@login_required
def customer_edit(request, user_id):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Forbidden")
    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect("admin_customers")
    else:
        form = UserForm(instance=user)
    return render(request, "admin/user_form.html", {"form": form, "object": user})


@login_required
def producers_list(request):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Forbidden")
    producers = Producer.objects.select_related("user").all()
    return render(request, "admin/producers_list.html", {"producers": producers})


@login_required
def producer_edit(request, pk):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Forbidden")
    producer = get_object_or_404(Producer, pk=pk)
    if request.method == "POST":
        form = ProducerForm(request.POST, instance=producer)
        if form.is_valid():
            form.save()
            return redirect("admin_producers")
    else:
        form = ProducerForm(instance=producer)
    return render(request, "admin/producer_form.html", {"form": form, "object": producer})


@login_required
def orders_list(request):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Forbidden")
    orders = Order.objects.select_related("customer").order_by("-created_at")
    return render(request, "admin/orders_list.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Forbidden")
    order = get_object_or_404(Order, pk=pk)
    return render(request, "admin/order_detail.html", {"order": order})


@login_required
def order_create(request):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Forbidden")
    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("admin_orders")
    else:
        form = OrderForm()
    return render(request, "admin/order_form.html", {"form": form})


@login_required
def order_edit(request, pk):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Forbidden")
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            return redirect("admin_orders")
    else:
        form = OrderForm(instance=order)
    return render(request, "admin/order_form.html", {"form": form, "object": order})


@login_required
def order_delete(request, pk):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Forbidden")
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        order.delete()
        return redirect("admin_orders")
    return render(request, "admin/confirm_delete.html", {"object": order})
