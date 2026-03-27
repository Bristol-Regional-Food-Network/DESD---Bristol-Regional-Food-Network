from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


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
