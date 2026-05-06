from collections import OrderedDict
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods

from products.models import Product, StockAlert
from basket.models import Order, OrderItem, OrderStatusHistory
from products.models import Product
from users.decorators import role_required

from .models import Producer


ORDER_FILTERS = {"all", "paid", "partially_fulfilled", "fulfilled", "cancelled"}
ITEM_FILTERS = {"all", "pending", "fulfilled", "cancelled"}
SORT_OPTIONS = {"newest", "oldest", "total_desc", "total_asc"}

COMMISSION_RATE = Decimal("0.05")
PRODUCER_RATE = Decimal("0.95")
MONEY_PLACES = Decimal("0.01")

def _money(value):
    return Decimal(value or 0).quantize(MONEY_PLACES)

def _settlement_week_start(dt):
    date_value = timezone.localtime(dt).date() if hasattr(dt, "hour") else dt
    return date_value - timezone.timedelta(days=date_value.weekday())

def _producer_settlement_data(producer: Producer):
    fulfilled_items = (
        producer.order_items
        .filter(fulfilment_status="fulfilled")
        .select_related("order", "order__user", "product")
        .order_by("-order__created_at", "product_name")
    )
    weekly = OrderedDict()
    rows = []
    for item in fulfilled_items:
        week_start = _settlement_week_start(item.order.created_at)
        week_end = week_start + timezone.timedelta(days=6)
        gross = _money(item.line_total)
        commission = _money(gross * COMMISSION_RATE)
        payout = _money(gross * PRODUCER_RATE)
        if week_start not in weekly:
            weekly[week_start] = {
                "week_start": week_start,
                "week_end": week_end,
                "gross_sales": Decimal("0.00"),
                "commission": Decimal("0.00"),
                "payout": Decimal("0.00"),
                "order_count": set(),
                "item_count": 0,
                "status": "Processed" if week_end < timezone.localdate() else "Pending",
                "items": [],
            }
        group = weekly[week_start]
        group["gross_sales"] += gross
        group["commission"] += commission
        group["payout"] += payout
        group["order_count"].add(item.order_id)
        group["item_count"] += item.quantity
        group["items"].append(item)
        rows.append({
            "week_start": week_start,
            "week_end": week_end,
            "status": group["status"],
            "item": item,
            "gross": gross,
            "commission": commission,
            "payout": payout,
        })
    summaries = []
    for group in weekly.values():
        summaries.append({
            **group,
            "order_count": len(group["order_count"]),
            "gross_sales": _money(group["gross_sales"]),
            "commission": _money(group["commission"]),
            "payout": _money(group["payout"]),
        })
    return summaries, rows


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
    return OrderItem.objects.filter(producer=producer).select_related("order", "product", "order__user")


def _build_grouped_orders(order_items, sort_by: str = "newest"):
    grouped = OrderedDict()

    for item in order_items:
        order_id = item.order_id

        if order_id not in grouped:
            grouped[order_id] = {
                "order": item.order,
                "customer": item.order.user,
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
        line_total = item.line_total
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


def _get_grouped_orders(
    producer: Producer,
    order_status: str = "all",
    item_status: str = "all",
    search: str = "",
    sort_by: str = "newest",
):
    order_items = _base_order_items_queryset(producer)

    if order_status != "all":
        order_items = order_items.filter(order__status=order_status)

    if item_status != "all":
        order_items = order_items.filter(fulfilment_status=item_status)

    if search:
        search = search.strip()
        q = Q(product__name__icontains=search) | Q(order__user__username__icontains=search)
        if search.isdigit():
            q |= Q(order_id=int(search))
        order_items = order_items.filter(q)

    order_items = order_items.order_by("-order__created_at", "product__name")
    return _build_grouped_orders(order_items, sort_by=sort_by)


def _producer_reports_context(producer: Producer):
    my_products = producer.products.all().order_by("name")
    my_order_items = producer.order_items.select_related("order", "product", "order__user")
    fulfilled_items = my_order_items.filter(fulfilment_status="fulfilled")

    week_ago = timezone.now() - timezone.timedelta(days=7)
    day_ago = timezone.now() - timezone.timedelta(days=1)

    total_earnings = sum((item.line_total for item in fulfilled_items), Decimal("0.00"))
    earnings_this_week = sum(
        (item.line_total for item in fulfilled_items.filter(order__created_at__gte=week_ago)),
        Decimal("0.00"),
    )
    items_sold = fulfilled_items.aggregate(total=Sum("quantity"))["total"] or 0

    fulfilled_order_entries = _build_grouped_orders(
        fulfilled_items.order_by("-order__created_at", "product__name"),
        sort_by="newest",
    )

    average_order_value = (
        sum((entry["producer_total"] for entry in fulfilled_order_entries), Decimal("0.00")) / len(fulfilled_order_entries)
        if fulfilled_order_entries else Decimal("0.00")
    )

    recent_new_orders = my_order_items.filter(order__created_at__gte=day_ago).values("order_id").distinct().count()
    pending_order_count = my_order_items.filter(fulfilment_status="pending").values("order_id").distinct().count()
    settlement_summaries, settlement_rows = _producer_settlement_data(producer)

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
        "settlement_summaries": settlement_summaries,
        "settlement_rows": settlement_rows,
        "status_badge_class": _status_badge_class,
    }


def index(request):
    return render(request, "producers/index.html")


@login_required
@role_required("producer")
def dashboard(request):
    producer = getattr(request.user, "producer", None)

    if producer is None:
        return render(
            request,
            "producers/dashboard.html",
            {
                "producer": None,
                "my_products": [],
                "seasonal_products": [],
                "discounted_products": [],
                "surplus_products": [],
                "all_products": [],
                "upcoming_season_products": [],
                "active_stock_alerts": [],
            },
        )

    my_products = Product.objects.filter(producer=producer).order_by("-id")
    seasonal_products = my_products.filter(section=Product.SECTION_SEASONAL)
    discounted_products = my_products.filter(section=Product.SECTION_DISCOUNTED)
    surplus_products = my_products.filter(section=Product.SECTION_SURPLUS)
    all_products = my_products.filter(section=Product.SECTION_ALL)
    upcoming_season_products = [p for p in my_products if p.season_starts_next_month]

    active_stock_alerts = StockAlert.objects.filter(
        product__producer=producer,
        is_resolved=False,
    ).select_related("product")

    return render(
        request,
        "producers/dashboard.html",
        {
            "producer": producer,
            "my_products": my_products,
            "seasonal_products": seasonal_products,
            "discounted_products": discounted_products,
            "surplus_products": surplus_products,
            "all_products": all_products,
            "upcoming_season_products": upcoming_season_products,
            "active_stock_alerts": active_stock_alerts,
        },
    )


@login_required
@role_required("producer")
def reports(request):
    producer = getattr(request.user, "producer", None)

    if producer is None:
        messages.error(request, "Producer profile not found.")
        return render(
            request,
            "producers/reports.html",
            {
                "producer": None,
                "my_products": [],
                "product_count": 0,
                "order_count": 0,
                "pending_items": 0,
                "fulfilled_items": 0,
                "cancelled_items": 0,
                "recent_order_items": [],
                "total_earnings": Decimal("0.00"),
                "earnings_this_week": Decimal("0.00"),
                "items_sold": 0,
                "average_order_value": Decimal("0.00"),
                "recent_new_orders": 0,
                "pending_order_count": 0,
                "settlement_summaries": [],
                "settlement_rows": [],
            },
        )

    return render(request, "producers/reports.html", _producer_reports_context(producer))


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
            "status_badge_class": _status_badge_class,
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
        .select_related("order", "product", "order__user")
        .order_by("product__name")
    )

    if not producer_items:
        messages.error(request, "Order not found for this producer.")
        return redirect("producers:producer_orders")

    order = producer_items[0].order
    _sync_order_status(order)
    producer_total = sum((item.line_total for item in producer_items), Decimal("0.00"))
    pending_items = [item for item in producer_items if item.fulfilment_status == "pending"]
    fulfilled_items = [item for item in producer_items if item.fulfilment_status == "fulfilled"]
    status_history = OrderStatusHistory.objects.filter(order=order, order_item__producer=producer).select_related("order_item", "changed_by")

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
            "status_badge_class": _status_badge_class,
            "status_history": status_history,
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
    producer_note = request.POST.get("status_note", "").strip()
    allowed_statuses = {"pending", "fulfilled"}

    if new_status not in allowed_statuses:
        messages.error(request, "Producers can only set items to pending or fulfilled.")
        return redirect("producers:producer_order_detail", order_id=order_item.order_id)

    if order_item.order.status == "cancelled" or order_item.fulfilment_status == "cancelled":
        messages.error(request, "You cannot change items from a cancelled order.")
        return redirect("producers:producer_order_detail", order_id=order_item.order_id)

    product_name = order_item.product.name if order_item.product else order_item.product_name

    if order_item.fulfilment_status == new_status:
        messages.info(request, f"{product_name} is already marked as {new_status}.")
        return redirect("producers:producer_order_detail", order_id=order_item.order_id)

    old_status = order_item.fulfilment_status
    order_item.fulfilment_status = new_status
    order_item.save(update_fields=["fulfilment_status"])
    OrderStatusHistory.objects.create(
        order=order_item.order,
        order_item=order_item,
        producer_order=order_item.producer_order,
        old_status=old_status,
        new_status=new_status,
        note=producer_note,
        changed_by=request.user,
    )
    _sync_order_status(order_item.order)

    messages.success(request, f"Updated {product_name} to {new_status.replace('_', ' ')}.")
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

    bulk_note = request.POST.get("status_note", "Bulk marked as fulfilled").strip()
    updated = 0
    for item in producer_items.exclude(fulfilment_status__in=["fulfilled", "cancelled"]):
        old_status = item.fulfilment_status
        item.fulfilment_status = "fulfilled"
        item.save(update_fields=["fulfilment_status"])
        OrderStatusHistory.objects.create(
            order=item.order,
            order_item=item,
            producer_order=item.producer_order,
            old_status=old_status,
            new_status="fulfilled",
            note=bulk_note,
            changed_by=request.user,
        )
        updated += 1

    _sync_order_status(order)

    if updated:
        messages.success(request, f"Marked {updated} line(s) as fulfilled.")
    else:
        messages.info(request, "No pending lines were available to fulfil.")

    return redirect("producers:producer_order_detail", order_id=order_id)



@login_required
@role_required("producer")
def settlement_csv(request):
    producer = getattr(request.user, "producer", None)
    if producer is None:
        messages.error(request, "Producer profile not found.")
        return redirect("producers:producer_reports")

    _, rows = _producer_settlement_data(producer)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="producer_settlements.csv"'
    response.write("Week Start,Week End,Settlement Status,Order ID,Customer,Product,Quantity,Gross Sales,Network Commission 5%,Producer Payout 95%\n")
    for row in rows:
        item = row["item"]
        customer = item.order.user.username if item.order.user else item.order.cardholder_name
        response.write(
            f"{row['week_start']},{row['week_end']},{row['status']},{item.order_id},{customer},{item.product_name},{item.quantity},{row['gross']},{row['commission']},{row['payout']}\n"
        )
    return response


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
    data = _producer_to_dict(producer)
    data["products"] = [
        {
            "id": product.id,
            "name": product.name,
            "price": str(product.price),
            "stock": product.stock,
            "availability_mode": product.availability_mode,
            "season_range_display": product.season_range_display,
            "customer_status": product.customer_status,
            "is_visible_to_customers": product.is_visible_to_customers,
            "is_surplus": product.is_surplus,
            "surplus_discount_percent": product.surplus_discount_percent,
            "surplus_note": product.surplus_note,
            "surplus_expires_at": product.surplus_expires_at.isoformat() if product.surplus_expires_at else None,
            "is_surplus_active": product.is_surplus_active,
            "active_price": str(product.active_price),
        }
        for product in producer.products.all().order_by("-id")
    ]
    return JsonResponse(data)