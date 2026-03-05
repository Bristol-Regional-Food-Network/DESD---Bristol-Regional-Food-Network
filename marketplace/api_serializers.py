from __future__ import annotations

from typing import Any, Dict, Optional

from .models import (
    Category,
    Customer,
    Inventory,
    Order,
    OrderItem,
    Payment,
    Producer,
    Product,
)


def producer_to_dict(x: Producer) -> Dict[str, Any]:
    return {
        "id": x.id,
        "name": x.name,
        "email": x.email,
        "phone": x.phone,
        "address": x.address,
        "postcode": x.postcode,
        "is_active": x.is_active,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    }


def customer_to_dict(x: Customer) -> Dict[str, Any]:
    return {
        "id": x.id,
        "full_name": x.full_name,
        "email": x.email,
        "phone": x.phone,
        "postcode": x.postcode,
        "is_active": x.is_active,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    }


def category_to_dict(x: Category) -> Dict[str, Any]:
    return {"id": x.id, "name": x.name}


def inventory_to_dict(inv: Inventory) -> Dict[str, Any]:
    return {
        "stock_qty": inv.stock_qty,
        "available_from": inv.available_from.isoformat() if inv.available_from else None,
        "available_to": inv.available_to.isoformat() if inv.available_to else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


def product_to_dict(p: Product) -> Dict[str, Any]:
    inv = getattr(p, "inventory", None)
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "unit": p.unit,
        "price": str(p.price),
        "is_active": p.is_active,
        "producer": {"id": p.producer_id, "name": p.producer.name},
        "category": {"id": p.category_id, "name": p.category.name},
        "harvest_date": p.harvest_date.isoformat() if p.harvest_date else None,
        "best_before_date": p.best_before_date.isoformat() if p.best_before_date else None,
        "is_organic": p.is_organic,
        "allergen_info": p.allergen_info,
        "origin_notes": p.origin_notes,
        "inventory": None if not inv else inventory_to_dict(inv),
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def order_item_to_dict(i: OrderItem) -> Dict[str, Any]:
    return {
        "id": i.id,
        "product": {"id": i.product_id, "name": i.product.name},
        "producer": {"id": i.producer_id, "name": i.producer.name},
        "quantity": i.quantity,
        "unit_price_at_purchase": str(i.unit_price_at_purchase) if i.unit_price_at_purchase is not None else None,
        "line_total": str(i.line_total),
    }


def payment_to_dict(p: Payment) -> Dict[str, Any]:
    return {
        "id": p.id,
        "provider": p.provider,
        "provider_ref": p.provider_ref,
        "amount_paid": str(p.amount_paid),
        "currency": p.currency,
        "status": p.status,
        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def order_to_dict(o: Order, include_items: bool = True, include_payment: bool = True) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "id": o.id,
        "customer": {"id": o.customer_id, "full_name": o.customer.full_name, "email": o.customer.email},
        "status": o.status,
        "fulfilment_method": o.fulfilment_method,
        "delivery_notes": o.delivery_notes,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "subtotal_amount": str(o.subtotal_amount),
        "commission_amount": str(o.commission_amount),
        "total_amount": str(o.total_amount),
    }
    if include_items:
        data["items"] = [order_item_to_dict(i) for i in o.items.all()]
    if include_payment:
        pay = getattr(o, "payment", None)
        data["payment"] = None if not pay else payment_to_dict(pay)
    return data
