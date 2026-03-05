from __future__ import annotations

from typing import Any, Dict, List

from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .api_common import json_error, parse_json
from .api_serializers import order_to_dict
from .models import Customer, Inventory, Order, OrderItem, Payment, Product


def _ensure_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = payload.get("items")
    if not isinstance(items, list) or len(items) == 0:
        raise ValueError("items must be a non-empty list")
    for it in items:
        if not isinstance(it, dict):
            raise ValueError("each item must be an object")
        if "product_id" not in it or "quantity" not in it:
            raise ValueError("each item requires product_id and quantity")
    return items


@csrf_exempt
def orders_collection(request: HttpRequest):
    if request.method == "GET":
        qs = Order.objects.select_related("customer").prefetch_related("items__product", "items__producer").order_by("-created_at")
        customer_id = request.GET.get("customer_id")
        status = request.GET.get("status")
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if status:
            qs = qs.filter(status=status)
        return JsonResponse([order_to_dict(o) for o in qs], safe=False)

    if request.method == "POST":
        payload = parse_json(request)
        if payload is None:
            return json_error("Invalid JSON body.", 400)

        if "customer_id" not in payload:
            return json_error("Missing required field.", 400, missing=["customer_id"])

        try:
            customer = Customer.objects.get(id=payload["customer_id"])
        except Customer.DoesNotExist:
            return json_error("customer_id not found.", 404)

        fulfilment_method = payload.get("fulfilment_method", Order.Fulfilment.COLLECTION)
        if fulfilment_method not in Order.Fulfilment.values:
            return json_error("Invalid fulfilment_method.", 400)

        delivery_notes = str(payload.get("delivery_notes", "")).strip()

        try:
            items = _ensure_items(payload)
        except ValueError as e:
            return json_error(str(e), 400)

        with transaction.atomic():
            order = Order.objects.create(
                customer=customer,
                fulfilment_method=fulfilment_method,
                delivery_notes=delivery_notes,
            )

            # lock products/inventory for update to avoid oversell
            for it in items:
                try:
                    pid = int(it["product_id"])
                    qty = int(it["quantity"])
                except (TypeError, ValueError):
                    return json_error("product_id and quantity must be integers.", 400)

                if qty < 1:
                    return json_error("quantity must be >= 1.", 400)

                try:
                    product = Product.objects.select_related("producer", "category").select_for_update().get(id=pid)
                except Product.DoesNotExist:
                    return json_error(f"Product {pid} not found.", 404)

                if not product.is_active:
                    return json_error(f"Product {pid} is not active.", 400)

                inv, _ = Inventory.objects.select_for_update().get_or_create(product=product)
                if inv.stock_qty < qty:
                    return json_error("Insufficient stock.", 409, product_id=pid, available=inv.stock_qty, requested=qty)

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    producer=product.producer,
                    quantity=qty,
                )

                inv.stock_qty -= qty
                inv.save(update_fields=["stock_qty", "updated_at"])

            order.recalculate_totals(save=True)

        order = Order.objects.select_related("customer").prefetch_related("items__product", "items__producer").get(id=order.id)
        return JsonResponse(order_to_dict(order), status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def order_resource(request: HttpRequest, order_id: int):
    try:
        order = Order.objects.select_related("customer").prefetch_related("items__product", "items__producer").get(id=order_id)
    except Order.DoesNotExist:
        return json_error("Order not found.", 404)

    if request.method == "GET":
        return JsonResponse(order_to_dict(order))

    if request.method in ("PATCH", "PUT"):
        payload = parse_json(request)
        if payload is None:
            return json_error("Invalid JSON body.", 400)

        new_status = payload.get("status")
        if not new_status:
            return json_error("Missing 'status' field.", 400)

        if new_status not in Order.Status.values:
            return json_error("Invalid status.", 400, allowed=list(Order.Status.values))

        with transaction.atomic():
            # Reload and lock
            order_locked = Order.objects.select_for_update().prefetch_related("items__product").get(id=order.id)

            old_status = order_locked.status
            if old_status == new_status:
                return JsonResponse(order_to_dict(order_locked))

            # If cancelling and not already cancelled, restock inventory
            if new_status == Order.Status.CANCELLED and old_status != Order.Status.CANCELLED:
                for item in order_locked.items.all():
                    inv, _ = Inventory.objects.select_for_update().get_or_create(product=item.product)
                    inv.stock_qty += item.quantity
                    inv.save(update_fields=["stock_qty", "updated_at"])

            order_locked.status = new_status
            order_locked.save(update_fields=["status"])

        order = Order.objects.select_related("customer").prefetch_related("items__product", "items__producer").get(id=order.id)
        return JsonResponse(order_to_dict(order))

    if request.method == "DELETE":
        # destructive delete is rarely wanted for orders; keep for admin/testing
        with transaction.atomic():
            order_locked = Order.objects.select_for_update().prefetch_related("items__product").get(id=order.id)
            # restock
            if order_locked.status != Order.Status.CANCELLED:
                for item in order_locked.items.all():
                    inv, _ = Inventory.objects.select_for_update().get_or_create(product=item.product)
                    inv.stock_qty += item.quantity
                    inv.save(update_fields=["stock_qty", "updated_at"])
            order_locked.delete()
        return JsonResponse({"deleted": True})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def order_payment_resource(request: HttpRequest, order_id: int):
    """Create/Update payment for an order (simple test provider)."""
    try:
        order = Order.objects.select_related("customer").get(id=order_id)
    except Order.DoesNotExist:
        return json_error("Order not found.", 404)

    if request.method == "GET":
        pay = getattr(order, "payment", None)
        return JsonResponse({"payment": None if not pay else {
            "id": pay.id,
            "status": pay.status,
            "amount_paid": str(pay.amount_paid),
            "currency": pay.currency,
            "paid_at": pay.paid_at.isoformat() if pay.paid_at else None,
        }})

    if request.method in ("POST", "PUT", "PATCH"):
        payload = parse_json(request)
        if payload is None:
            return json_error("Invalid JSON body.", 400)

        status = payload.get("status", Payment.Status.PAID)
        if status not in Payment.Status.values:
            return json_error("Invalid payment status.", 400, allowed=list(Payment.Status.values))

        amount = payload.get("amount_paid")
        if amount is None:
            amount = str(order.total_amount)

        provider = str(payload.get("provider", "test")).strip() or "test"
        provider_ref = str(payload.get("provider_ref", "")).strip()

        with transaction.atomic():
            pay, _ = Payment.objects.select_for_update().get_or_create(
                order=order,
                defaults={
                    "provider": provider,
                    "provider_ref": provider_ref,
                    "amount_paid": amount,
                    "currency": str(payload.get("currency", "GBP")).strip() or "GBP",
                    "status": status,
                    "paid_at": timezone.now() if status == Payment.Status.PAID else None,
                },
            )
            if pay:
                pay.provider = provider
                pay.provider_ref = provider_ref
                pay.amount_paid = amount
                pay.currency = str(payload.get("currency", pay.currency)).strip() or pay.currency
                pay.status = status
                pay.paid_at = timezone.now() if status == Payment.Status.PAID else None
                pay.save()

            # If paid, mark order as paid (simple behaviour)
            if status == Payment.Status.PAID and order.status == Order.Status.PENDING:
                Order.objects.filter(id=order.id).update(status=Order.Status.PAID)

        return JsonResponse({"updated": True})

    return JsonResponse({"error": "Method not allowed"}, status=405)
