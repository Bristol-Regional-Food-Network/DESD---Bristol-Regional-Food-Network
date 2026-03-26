from collections import OrderedDict
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods

from basket.models import Order, OrderItem
from products.models import Product
from users.decorators import role_required

from .models import Producer


ORDER_FILTERS = {"all", "paid", "partially_fulfilled", "fulfilled", "cancelled"}
ITEM_FILTERS = {"all", "pending", "fulfilled", "cancelled"}
SORT_OPTIONS = {"newest", "oldest", "total_desc", "total_asc"}


def _producer_to_dict(producer: Producer):
    return {
        "id": producer.id,
        "display_name": producer.display_name,
        "bio": producer.bio,
        "location": producer.location,
        "phone": producer.phone,
        "website": producer.website,
        "product_count": producer.products.count(),
    }


def _status_badge_class(status: str) -> str:
    mapping = {
        "pending": "warning",
        "paid": "primary",
        "partially_fulfilled": "info",
        "fulfilled": "success",
        "cancelled": "danger",
    }
    return mapping.get(status, "secondary")


def _sync_order_status(order: Order) -> str:
    items = list(order.items.all())
    if not items:
        new_status = "paid"
    elif all(item.fulfilment_status == "cancelled" for item in items):
        new_status = "cancelled"
    elif all(item.fulfilment_status == "fulfilled" for item in items):
        new_status = "fulfilled"
    elif any(item.fulfilment_status in {"fulfilled", "cancelled"} for item in items):
        new_status = "partially_fulfilled"
    else:
        new_status = "paid"

    if order.status != new_status:
        order.status = new_status
        order.save(update_fields=["status"])
    return new_status


def _base_order_items_queryset(producer: Producer):
    return OrderItem.objects.filter(producer=producer).select_related("order", "product", "order__customer")


def _build_grouped_orders(order_items, sort_by: str = "newest"):
    grouped = OrderedDict()

    for item in order_items:
        order_id = item.order_id
        if order_id not in grouped:
            grouped[order_id] = {
                "order": item.order,
                "customer": item.order.customer,
                "items": [],
                "producer_total": Decimal("0.00"),
                "item_count": 0,
                "line_count": 0,
                "pending_count": 0,
                "fulfilled_count": 0,
                "cancelled_count": 0,
                "has_pending": False,
                "has_fulfilled": False,
                "has_cancelled": False,
            }

        group = grouped[order_id]
        line_total = item.line_total()
        group["items"].append(item)
        group["producer_total"] += line_total
        group["item_count"] += item.quantity
        group["line_count"] += 1
        if item.fulfilment_status == "pending":
            group["pending_count"] += 1
            group["has_pending"] = True
        elif item.fulfilment_status == "fulfilled":
            group["fulfilled_count"] += 1
            group["has_fulfilled"] = True
        elif item.fulfilment_status == "cancelled":
            group["cancelled_count"] += 1
            group["has_cancelled"] = True

    entries = list(grouped.values())
    if sort_by == "oldest":
        entries.sort(key=lambda e: e["order"].created_at)
    elif sort_by == "total_desc":
        entries.sort(key=lambda e: (e["producer_total"], e["order"].created_at), reverse=True)
    elif sort_by == "total_asc":
        entries.sort(key=lambda e: (e["producer_total"], e["order"].created_at))
    else:
        entries.sort(key=lambda e: e["order"].created_at, reverse=True)
    return entries


def _get_grouped_orders(producer: Producer, order_status: str = "all", item_status: str = "all", search: str = "", sort_by: str = "newest"):
    order_items = _base_order_items_queryset(producer)

    if order_status != "all":
        order_items = order_items.filter(order__status=order_status)

    if item_status != "all":
        order_items = order_items.filter(fulfilment_status=item_status)

    if search:
        search = search.strip()
        q = Q(product__name__icontains=search) | Q(order__customer__username__icontains=search)
        if search.isdigit():
            q |= Q(order_id=int(search))
        order_items = order_items.filter(q)

    order_items = order_items.order_by("-order__created_at", "product__name")
    return _build_grouped_orders(order_items, sort_by=sort_by)


def _producer_dashboard_context(producer: Producer):
    my_products = producer.products.all().order_by("name")
    my_order_items = producer.order_items.select_related("order", "product", "order__customer")
    fulfilled_items = my_order_items.filter(fulfilment_status="fulfilled")
    week_ago = timezone.now() - timezone.timedelta(days=7)
    day_ago = timezone.now() - timezone.timedelta(days=1)

    total_earnings = sum((item.line_total() for item in fulfilled_items), Decimal("0.00"))
    earnings_this_week = sum((item.line_total() for item in fulfilled_items.filter(order__created_at__gte=week_ago)), Decimal("0.00"))
    items_sold = fulfilled_items.aggregate(total=Sum("quantity"))["total"] or 0
    fulfilled_order_ids = list(fulfilled_items.values_list("order_id", flat=True).distinct())
    fulfilled_order_entries = _build_grouped_orders(fulfilled_items.order_by("-order__created_at", "product__name"), sort_by="newest")
    average_order_value = (
        sum((entry["producer_total"] for entry in fulfilled_order_entries), Decimal("0.00")) / len(fulfilled_order_entries)
        if fulfilled_order_entries else Decimal("0.00")
    )

    recent_new_orders = my_order_items.filter(order__created_at__gte=day_ago).values("order_id").distinct().count()
    pending_order_count = my_order_items.filter(fulfilment_status="pending").values("order_id").distinct().count()

    return {
        "producer": producer,
        "my_products": my_products,
        "product_count": my_products.count(),
        "order_count": my_order_items.values("order_id").distinct().count(),
        "pending_items": my_order_items.filter(fulfilment_status="pending").count(),
        "fulfilled_items": my_order_items.filter(fulfilment_status="fulfilled").count(),
        "cancelled_items": my_order_items.filter(fulfilment_status="cancelled").count(),
        "recent_order_items": my_order_items.order_by("-order__created_at", "product__name")[:5],
        "total_earnings": total_earnings,
        "earnings_this_week": earnings_this_week,
        "items_sold": items_sold,
        "average_order_value": average_order_value,
        "recent_new_orders": recent_new_orders,
        "pending_order_count": pending_order_count,
    }


@login_required
@role_required("producer")
def index(request):
    return redirect("producers:producer_dashboard")


@login_required
@role_required("producer")
def dashboard(request):
    producer = Producer.objects.filter(user=request.user).first()
    if producer is None:
        messages.error(request, "Producer profile not found.")
        return render(request, "producers/dashboard.html", {"producer": None, "my_products": []})

    return render(request, "producers/dashboard.html", _producer_dashboard_context(producer))


@login_required
@role_required("producer")
def producer_orders(request):
    producer = getattr(request.user, "producer", None)

    if producer is None:
        messages.error(request, "Producer profile not found.")
        return render(
            request,
            "producers/orders.html",
            {
                "producer": None,
                "grouped_orders": [],
                "selected_order_status": "all",
                "selected_item_status": "all",
                "selected_sort": "newest",
                "search_query": "",
                "order_status_options": Order.STATUS_CHOICES,
            },
        )

    selected_order_status = request.GET.get("status", "all")
    if selected_order_status not in ORDER_FILTERS:
        selected_order_status = "all"

    selected_item_status = request.GET.get("item_status", "all")
    if selected_item_status not in ITEM_FILTERS:
        selected_item_status = "all"

    selected_sort = request.GET.get("sort", "newest")
    if selected_sort not in SORT_OPTIONS:
        selected_sort = "newest"

    search_query = request.GET.get("q", "").strip()

    grouped_orders = _get_grouped_orders(
        producer,
        selected_order_status,
        selected_item_status,
        search=search_query,
        sort_by=selected_sort,
    )

    return render(
        request,
        "producers/orders.html",
        {
            "producer": producer,
            "grouped_orders": grouped_orders,
            "selected_order_status": selected_order_status,
            "selected_item_status": selected_item_status,
            "selected_sort": selected_sort,
            "search_query": search_query,
            "order_status_options": Order.STATUS_CHOICES,
        },
    )


@login_required
@role_required("producer")
def producer_order_detail(request, order_id):
    producer = getattr(request.user, "producer", None)
    if producer is None:
        messages.error(request, "Producer profile not found.")
        return redirect("producers:producer_orders")

    producer_items = list(
        OrderItem.objects.filter(order_id=order_id, producer=producer)
        .select_related("order", "product", "order__customer")
        .order_by("product__name")
    )

    if not producer_items:
        messages.error(request, "Order not found for this producer.")
        return redirect("producers:producer_orders")

    order = producer_items[0].order
    _sync_order_status(order)
    producer_total = sum((item.line_total() for item in producer_items), Decimal("0.00"))
    pending_items = [item for item in producer_items if item.fulfilment_status == "pending"]
    fulfilled_items = [item for item in producer_items if item.fulfilment_status == "fulfilled"]

    return render(
        request,
        "producers/order_detail.html",
        {
            "producer": producer,
            "order": order,
            "producer_items": producer_items,
            "producer_total": producer_total,
            "pending_line_count": len(pending_items),
            "fulfilled_line_count": len(fulfilled_items),
            "all_items_finalised": all(item.fulfilment_status in {"fulfilled", "cancelled"} for item in producer_items),
        },
    )


@login_required
@role_required("producer")
@require_POST
def update_order_item_status(request, item_id):
    producer = getattr(request.user, "producer", None)
    if producer is None:
        messages.error(request, "Producer profile not found.")
        return redirect("producers:producer_orders")

    order_item = get_object_or_404(
        OrderItem.objects.select_related("order", "product"),
        id=item_id,
        producer=producer,
    )

    new_status = request.POST.get("fulfilment_status", "").strip()
    allowed_statuses = {"pending", "fulfilled"}
    if new_status not in allowed_statuses:
        messages.error(request, "Producers can only set items to pending or fulfilled.")
        return redirect("producers:producer_order_detail", order_id=order_item.order_id)

    if order_item.order.status == "cancelled" or order_item.fulfilment_status == "cancelled":
        messages.error(request, "You cannot change items from a cancelled order.")
        return redirect("producers:producer_order_detail", order_id=order_item.order_id)

    if order_item.fulfilment_status == new_status:
        messages.info(request, f"{order_item.product.name} is already marked as {new_status}.")
        return redirect("producers:producer_order_detail", order_id=order_item.order_id)

    order_item.fulfilment_status = new_status
    order_item.save(update_fields=["fulfilment_status"])
    _sync_order_status(order_item.order)

    messages.success(request, f"Updated {order_item.product.name} to {new_status.replace('_', ' ')}.")
    return redirect("producers:producer_order_detail", order_id=order_item.order_id)


@login_required
@role_required("producer")
@require_POST
def bulk_fulfil_order(request, order_id):
    producer = getattr(request.user, "producer", None)
    if producer is None:
        messages.error(request, "Producer profile not found.")
        return redirect("producers:producer_orders")

    producer_items = OrderItem.objects.filter(order_id=order_id, producer=producer).select_related("order")
    if not producer_items.exists():
        messages.error(request, "Order not found for this producer.")
        return redirect("producers:producer_orders")

    order = producer_items.first().order
    if order.status == "cancelled":
        messages.error(request, "Cancelled orders cannot be fulfilled.")
        return redirect("producers:producer_order_detail", order_id=order_id)

    updated = producer_items.exclude(fulfilment_status__in=["fulfilled", "cancelled"]).update(fulfilment_status="fulfilled")
    _sync_order_status(order)

    if updated:
        messages.success(request, f"Marked {updated} line(s) as fulfilled.")
    else:
        messages.info(request, "No pending lines were available to fulfil.")
    return redirect("producers:producer_order_detail", order_id=order_id)


def list_producers(request):
    producers = Producer.objects.all().order_by("display_name")
    return render(request, "producers/list.html", {"producers": producers})


def producer_detail(request, producer_id):
    producer = get_object_or_404(Producer, id=producer_id)
    return render(request, "producers/detail.html", {"producer": producer})


@require_http_methods(["GET"])
def api_producer_collection(request: HttpRequest):
    producers = Producer.objects.all().order_by("display_name")
    location = request.GET.get("location")
    if location:
        producers = producers.filter(location__icontains=location)
    return JsonResponse([_producer_to_dict(p) for p in producers], safe=False)


@require_http_methods(["GET"])
def api_producer_resource(request: HttpRequest, producer_id: int):
    producer = get_object_or_404(Producer, id=producer_id)
    return JsonResponse(_producer_to_dict(producer))
