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
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'manager':
        raise PermissionDenied()
    return render(request, 'managers/dashboard.html')


@login_required
def orders_list(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'manager':
        raise PermissionDenied()
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
        orders = Order.objects.select_related('user').all().order_by('-created_at')
        status_choices = getattr(Order, 'STATUS_CHOICES', [])
        return render(request, 'managers/orders_list.html', {'orders': orders, 'status_choices': status_choices})
    except Exception:
        import sqlite3
        from types import SimpleNamespace
        from datetime import datetime
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
                dt = None
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at)
                    except Exception:
                        try:
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
# TC-018: Materialise any recurring orders that are now due.
# ---------------------------------------------------------------------------
def _materialise_due_recurring_orders():
    from uuid import uuid4
    from basket.models import Order, OrderItem, ProducerOrder, RecurringOrder

    today = timezone.localdate()
    due = RecurringOrder.objects.filter(
        status=RecurringOrder.STATUS_ACTIVE,
        next_run_date__lte=today,
    ).prefetch_related("items")

    for template in due:
        items = list(template.items.all())
        if not items:
            continue

        groups = {}
        for item in items:
            qty = item.effective_next_quantity
            if qty <= 0:
                continue
            price = item.price or Decimal("0.00")
            key = item.producer_name or "Unknown Producer"
            groups.setdefault(key, []).append({
                "item": item,
                "qty": qty,
                "subtotal": _money((item.price or Decimal("0.00")) * qty),
            })

        if not groups:
            continue

        subtotal = _money(sum(e["subtotal"] for g in groups.values() for e in g))
        commission = _money(subtotal * COMMISSION_RATE)
        grand_total = _money(subtotal + commission)

        order = Order.objects.create(
            user=template.user,
            producer_name=list(groups.keys())[0] if len(groups) == 1 else "Multiple Producers",
            cardholder_name=template.cardholder_name,
            card_last4=template.card_last4,
            billing_address=template.billing_address,
            city=template.city,
            postcode=template.postcode,
            country=template.country,
            delivery_date=template.next_delivery_date,
            payment_reference=f"RECUR-{uuid4().hex[:12].upper()}",
            total_amount=grand_total,
            commission_amount=commission,
            producer_amount=_money(subtotal * PRODUCER_RATE),
            status=Order.STATUS_PENDING,
        )

        for producer_name, entries in groups.items():
            group_subtotal = _money(sum(e["subtotal"] for e in entries))
            po = ProducerOrder.objects.create(
                order=order,
                producer_name=producer_name,
                delivery_date=template.next_delivery_date,
                subtotal_amount=group_subtotal,
                payout_amount=_money(group_subtotal * PRODUCER_RATE),
                status=ProducerOrder.STATUS_PENDING,
            )
            for entry in entries:
                item = entry["item"]
                OrderItem.objects.create(
                    order=order,
                    producer_order=po,
                    product=item.product,
                    producer=item.producer,
                    product_name=item.product_name,
                    producer_name=item.producer_name,
                    unit_display=item.unit_display,
                    price=item.price,
                    quantity=entry["qty"],
                )
                if item.next_quantity_override is not None:
                    item.next_quantity_override = None
                    item.save(update_fields=["next_quantity_override"])

        delta = timedelta(weeks=1) if template.frequency == RecurringOrder.FREQ_WEEKLY else timedelta(weeks=2)
        next_run = template.next_run_date + delta
        days_ahead = (template.delivery_day - next_run.weekday()) % 7 or 7
        template.next_run_date = next_run
        template.next_delivery_date = next_run + timedelta(days=days_ahead)
        template.save(update_fields=["next_run_date", "next_delivery_date", "updated_at"])


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
    from basket.models import Order, RecurringOrder

    qs = (
        Order.objects
        .filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        .prefetch_related("items", "producer_orders")
        .order_by("-created_at")
    )

    if status_filter and status_filter != "recurring":
        qs = qs.filter(status=status_filter)
    elif status_filter == "recurring":
        qs = qs.none()

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
            "is_recurring": False,
        })

        total_order_value += subtotal
        total_commission += commission
        total_producer_payout += producer_total

    if not status_filter or status_filter == "recurring":
        # Fetch all active recurring orders regardless of created_at —
        # we expand each into occurrences within the report date range below.
        ro_qs = (
            RecurringOrder.objects
            .filter(status=RecurringOrder.STATUS_ACTIVE)
            .prefetch_related("items")
        )
        if producer_filter:
            ro_qs = ro_qs.filter(items__producer_name__icontains=producer_filter).distinct()

        for template in ro_qs:
            subtotal = template.template_total

            # Skip recurring orders with no items or zero value (e.g. items deleted)
            if subtotal <= 0:
                continue

            commission = _money(subtotal * COMMISSION_RATE)
            producer_total = _money(subtotal * PRODUCER_RATE)
            grand_total = _money(subtotal + commission)

            producer_breakdown = {}
            for item in template.items.all():
                key = item.producer_name or "Unknown Producer"
                producer_breakdown.setdefault(key, Decimal("0.00"))
                producer_breakdown[key] += item.line_total

            breakdown_list = [
                {"producer_name": k, "subtotal": _money(v), "payout": _money(v * PRODUCER_RATE)}
                for k, v in producer_breakdown.items()
            ]

            delta = timedelta(weeks=1) if template.frequency == RecurringOrder.FREQ_WEEKLY else timedelta(weeks=2)

            # Find the first occurrence on or after start_date
            occurrence = template.next_run_date
            if occurrence < start_date:
                # Fast-forward to the first occurrence within the range
                gap = (start_date - occurrence).days
                steps = gap // delta.days
                occurrence = occurrence + delta * steps
                if occurrence < start_date:
                    occurrence += delta

            # Emit one row per occurrence within the date range
            while occurrence <= end_date:
                rows.append({
                    "order_id": f"RO-{template.id}",
                    "created_at": timezone.make_aware(datetime.combine(occurrence, datetime.min.time())),
                    "customer": template.user.username if template.user else template.cardholder_name,
                    "status": f"Recurring ({template.get_frequency_display()})",
                    "status_code": "recurring",
                    "subtotal": _money(subtotal),
                    "commission": commission,
                    "producer_total": producer_total,
                    "order_total": grand_total,
                    "producer_breakdown": breakdown_list,
                    "is_recurring": True,
                })

                total_order_value += _money(subtotal)
                total_commission += commission
                total_producer_payout += producer_total

                occurrence += delta

    rows.sort(key=lambda r: r["created_at"], reverse=True)

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
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'manager':
        raise PermissionDenied()

    _materialise_due_recurring_orders()

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