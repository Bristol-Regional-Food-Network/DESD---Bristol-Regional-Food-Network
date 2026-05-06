"""
Stock alert utilities for Bristol Regional Food Network.
Called after stock is decremented on checkout, and after stock is updated.
"""
from django.utils import timezone


def check_and_create_stock_alert(product):
    """
    Check if product stock has fallen below threshold.
    Creates an alert if so, resolves existing alerts if stock is back above threshold.
    """
    from products.models import StockAlert

    threshold = product.low_stock_threshold
    current_stock = product.stock

    if current_stock < threshold:
        # Only create a new alert if there isn't an active unresolved one
        existing = StockAlert.objects.filter(
            product=product,
            is_resolved=False
        ).first()

        if not existing:
            StockAlert.objects.create(
                product=product,
                current_stock=current_stock,
                threshold=threshold,
            )
        else:
            # Update current stock on existing alert
            existing.current_stock = current_stock
            existing.save(update_fields=['current_stock'])
    else:
        # Stock is back above threshold — resolve any open alerts
        StockAlert.objects.filter(
            product=product,
            is_resolved=False
        ).update(
            is_resolved=True,
            resolved_at=timezone.now()
        )