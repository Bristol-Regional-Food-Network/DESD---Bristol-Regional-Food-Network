from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import csv

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone


@login_required
def manager_dashboard(request):
    # Only allow users with the `manager` role to access this view
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'manager':
        raise PermissionDenied()
    return render(request, 'managers/dashboard.html')


@login_required
def orders_list(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'manager':
        raise PermissionDenied()
    # Allow managers to update order status or delete orders via POST
    if request.method == 'POST':
        action = request.POST.get('action')
        order_id = request.POST.get('order_id')
        try:
            from basket.models import Order
            order = get_object_or_404(Order, pk=order_id)
            if action == 'update_status':
                new_status = request.POST.get('status')
                if new_status and new_status != order.status:
                    order.status = new_status
                    order.save()
                    messages.success(request, f"Order #{order.id} status updated to {order.get_status_display()}.")
            elif action == 'delete':
                order.delete()
                messages.success(request, f"Order #{order_id} deleted permanently.")
        except Exception:
            messages.error(request, 'Could not perform requested action.')
        return redirect('manager_orders')
    try:
        from basket.models import Order
        # Return all orders (include past orders) ordered by newest first
        orders = Order.objects.select_related('user').all().order_by('-created_at')
        status_choices = getattr(Order, 'STATUS_CHOICES', [])
        return render(request, 'managers/orders_list.html', {'orders': orders, 'status_choices': status_choices})
    except Exception:
        # Fallback: if migrations/schema are incomplete the ORM may raise
        # OperationalError for missing columns. Query sqlite directly and
        # build simple objects for the template.
        import sqlite3
        from types import SimpleNamespace
        from datetime import datetime
        # map status codes to display strings from the model choices if available
        status_map = {}
        try:
            from basket.models import Order as OrderModel
            status_map = {k: v for k, v in OrderModel.STATUS_CHOICES}
            status_choices = OrderModel.STATUS_CHOICES
        except Exception:
            status_map = {}
            status_choices = []

        db_path = 'db.sqlite3'
        results = []
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT id, cardholder_name, total_amount, status, delivery_date, created_at FROM basket_order ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
            for r in rows:
                _id, cardholder_name, total_amount, status, delivery_date, created_at = r
                # parse created_at if possible
                dt = None
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at)
                    except Exception:
                        try:
                            # fallback parse common sqlite format
                            dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            dt = None
                obj = SimpleNamespace(
                    id=_id,
                    user=None,
                    cardholder_name=cardholder_name,
                    total_amount=total_amount,
                    status=status,
                    delivery_date=delivery_date,
                    created_at=dt,
                    get_status_display=status_map.get(status, status),
                )
                results.append(obj)
        except Exception:
            results = []
        finally:
            try:
                conn.close()
            except Exception:
                pass

        return render(request, 'managers/orders_list.html', {'orders': results, 'status_choices': status_choices})


@login_required
def customers_list(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'manager':
        raise PermissionDenied()
    from django.contrib.auth.models import User
    from django.db.models import Prefetch
    # Prefetch orders (ordered by newest first) so the template can show previous orders per customer
    from basket.models import Order as OrderModel
    customers = (
        User.objects
        .filter(userprofile__role='customer')
        .select_related('userprofile')
        .prefetch_related(Prefetch('orders', queryset=OrderModel.objects.order_by('-created_at')))
    )
    return render(request, 'managers/customers_list.html', {'customers': customers})


@login_required
def producers_list(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'manager':
        raise PermissionDenied()
    try:
        from producers.models import Producer
        producers = Producer.objects.select_related('user').all()
    except Exception:
        producers = []
    return render(request, 'managers/producers_list.html', {'producers': producers})


# ---------------------------------------------------------------------------
# TC-025: Financial Reports / Network Commission
# ---------------------------------------------------------------------------
COMMISSION_RATE = Decimal("0.05")
PRODUCER_RATE = Decimal("0.95")


def _money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parse_date(raw, fallback):
    if not raw:
        return fallback
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return fallback


def _build_commission_dataset(start_date, end_date, producer_filter="", status_filter=""):
    """Compute commission rows for the given filters.

    Returns a tuple (rows, totals) where ``rows`` is a list of dicts with the
    full audit trail per order (including per-producer payout breakdown) and
    ``totals`` aggregates the period-level stats.
    """
    from basket.models import Order

    qs = (
        Order.objects
        .filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        .prefetch_related("items", "producer_orders")
        .order_by("-created_at")
    )

    if status_filter:
        qs = qs.filter(status=status_filter)

    if producer_filter:
        qs = qs.filter(producer_orders__producer_name__icontains=producer_filter).distinct()

    rows = []
    total_order_value = Decimal("0.00")
    total_commission = Decimal("0.00")
    total_producer_payout = Decimal("0.00")

    for order in qs:
        order_total = Decimal(order.total_amount or 0)
        subtotal = _money(order_total / (Decimal("1") + COMMISSION_RATE)) if order_total else Decimal("0.00")
        commission = _money(subtotal * COMMISSION_RATE)
        producer_total = _money(subtotal * PRODUCER_RATE)

        producer_breakdown = []
        for po in order.producer_orders.all():
            po_subtotal = Decimal(po.subtotal_amount or 0)
            po_payout = _money(po_subtotal * PRODUCER_RATE)
            producer_breakdown.append({
                "producer_name": po.producer_name,
                "subtotal": _money(po_subtotal),
                "payout": po_payout,
            })

        rows.append({
            "order_id": order.id,
            "created_at": order.created_at,
            "customer": order.user.username if order.user else order.cardholder_name,
            "status": order.get_status_display(),
            "status_code": order.status,
            "subtotal": subtotal,
            "commission": commission,
            "producer_total": producer_total,
            "order_total": _money(order_total),
            "producer_breakdown": producer_breakdown,
        })

        total_order_value += subtotal
        total_commission += commission
        total_producer_payout += producer_total

    totals = {
        "order_count": len(rows),
        "total_order_value": _money(total_order_value),
        "total_commission": _money(total_commission),
        "total_producer_payout": _money(total_producer_payout),
        "total_with_commission": _money(total_order_value + total_commission),
    }

    return rows, totals


def _ytd_totals():
    today = timezone.localdate()
    start_of_year = today.replace(month=1, day=1)
    _, totals = _build_commission_dataset(start_of_year, today)
    return totals


def _monthly_summary(months_back=6):
    today = timezone.localdate()
    summaries = []

    for i in range(months_back):
        anchor = today.replace(day=1)
        for _ in range(i):
            previous_month_end = anchor - timedelta(days=1)
            anchor = previous_month_end.replace(day=1)

        if anchor.month == 12:
            next_month = anchor.replace(year=anchor.year + 1, month=1, day=1)
        else:
            next_month = anchor.replace(month=anchor.month + 1, day=1)
        end_of_month = next_month - timedelta(days=1)

        _, totals = _build_commission_dataset(anchor, end_of_month)
        summaries.append({
            "label": anchor.strftime("%B %Y"),
            "start": anchor,
            "end": end_of_month,
            "totals": totals,
        })

    return summaries


@login_required
def financial_reports(request):
    """TC-025: Network commission report for system administrators / managers."""
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'manager':
        raise PermissionDenied()

    today = timezone.localdate()
    default_start = today - timedelta(days=14)
    start_date = _parse_date(request.GET.get("start"), default_start)
    end_date = _parse_date(request.GET.get("end"), today)
    producer_filter = request.GET.get("producer", "").strip()
    status_filter = request.GET.get("status", "").strip()

    rows, totals = _build_commission_dataset(
        start_date, end_date, producer_filter=producer_filter, status_filter=status_filter
    )

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="commission_report_{start_date}_{end_date}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            "Order ID", "Created", "Customer", "Status",
            "Subtotal (£)", "Commission 5% (£)",
            "Producer Total 95% (£)", "Order Total (£)",
            "Producer Breakdown",
        ])
        for row in rows:
            breakdown = "; ".join(
                f"{p['producer_name']}: subtotal £{p['subtotal']} -> payout £{p['payout']}"
                for p in row["producer_breakdown"]
            )
            writer.writerow([
                row["order_id"],
                row["created_at"].strftime("%Y-%m-%d %H:%M") if row["created_at"] else "",
                row["customer"],
                row["status"],
                row["subtotal"],
                row["commission"],
                row["producer_total"],
                row["order_total"],
                breakdown,
            ])
        writer.writerow([])
        writer.writerow(["Period totals"])
        writer.writerow(["Orders processed", totals["order_count"]])
        writer.writerow(["Total order value (subtotal)", totals["total_order_value"]])
        writer.writerow(["Total commission (5%)", totals["total_commission"]])
        writer.writerow(["Total producer payout (95%)", totals["total_producer_payout"]])
        writer.writerow(["Total billed including commission", totals["total_with_commission"]])
        return response

    status_choices = []
    try:
        from basket.models import Order as OrderModel
        status_choices = OrderModel.STATUS_CHOICES
    except Exception:
        status_choices = []

    return render(request, 'managers/financial_reports.html', {
        "rows": rows,
        "totals": totals,
        "start_date": start_date,
        "end_date": end_date,
        "producer_filter": producer_filter,
        "status_filter": status_filter,
        "status_choices": status_choices,
        "ytd_totals": _ytd_totals(),
        "monthly_summary": _monthly_summary(months_back=6),
        "commission_rate_pct": "5",
        "producer_rate_pct": "95",
    })


@login_required
def financial_report_detail(request, order_id):
    """Drill-down view for a single order's commission audit trail."""
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'manager':
        raise PermissionDenied()

    from basket.models import Order

    order = get_object_or_404(
        Order.objects.prefetch_related("items", "producer_orders"),
        pk=order_id,
    )

    order_total = Decimal(order.total_amount or 0)
    subtotal = _money(order_total / (Decimal("1") + COMMISSION_RATE)) if order_total else Decimal("0.00")
    commission = _money(subtotal * COMMISSION_RATE)
    producer_total = _money(subtotal * PRODUCER_RATE)

    producer_breakdown = []
    for po in order.producer_orders.all():
        po_subtotal = Decimal(po.subtotal_amount or 0)
        po_payout = _money(po_subtotal * PRODUCER_RATE)
        producer_breakdown.append({
            "producer_name": po.producer_name,
            "subtotal": _money(po_subtotal),
            "payout": po_payout,
            "delivery_date": po.delivery_date,
            "status": po.get_status_display(),
        })

    return render(request, 'managers/financial_report_detail.html', {
        "order": order,
        "subtotal": subtotal,
        "commission": commission,
        "producer_total": producer_total,
        "order_total": _money(order_total),
        "producer_breakdown": producer_breakdown,
    })
