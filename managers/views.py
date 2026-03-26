from django.shortcuts import render
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
    try:
        from basket.models import Order
        orders = Order.objects.select_related('user').all().order_by('-created_at')[:200]
    except Exception:
        orders = []
    return render(request, 'managers/orders_list.html', {'orders': orders})


@login_required
def customers_list(request):
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role != 'manager':
        raise PermissionDenied()
    from django.contrib.auth.models import User
    customers = User.objects.filter(userprofile__role='customer').select_related('userprofile')
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
