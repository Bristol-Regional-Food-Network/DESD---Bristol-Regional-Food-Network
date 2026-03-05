import json
from decimal import Decimal
from typing import Any, Dict, Optional

from django.http import JsonResponse, HttpRequest, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Product, Producer, Category, Inventory


def _json_error(message: str, status: int = 400, **extra):
    payload = {"error": message}
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=status)


def _parse_json(request: HttpRequest) -> Optional[Dict[str, Any]]:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def _product_to_dict(p: Product) -> Dict[str, Any]:
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
        "inventory": None if not inv else {
            "stock_qty": inv.stock_qty,
            "available_from": inv.available_from.isoformat() if inv.available_from else None,
            "available_to": inv.available_to.isoformat() if inv.available_to else None,
            "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        },
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@require_http_methods(["GET"])
def health(request: HttpRequest):
    return JsonResponse({"status": "ok"})


@require_http_methods(["GET"])
def producers_list(request: HttpRequest):
    qs = Producer.objects.all().order_by("id")
    data = [{
        "id": x.id,
        "name": x.name,
        "email": x.email,
        "phone": x.phone,
        "postcode": x.postcode,
        "is_active": x.is_active,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    } for x in qs]
    return JsonResponse(data, safe=False)


@require_http_methods(["GET"])
def categories_list(request: HttpRequest):
    qs = Category.objects.all().order_by("name")
    data = [{"id": c.id, "name": c.name} for c in qs]
    return JsonResponse(data, safe=False)


@csrf_exempt
def products_collection(request: HttpRequest):
    if request.method == "GET":
        qs = Product.objects.select_related("producer", "category").order_by("id")
        # optional filters
        producer_id = request.GET.get("producer_id")
        category_id = request.GET.get("category_id")
        active = request.GET.get("active")

        if producer_id:
            qs = qs.filter(producer_id=producer_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if active in ("true", "false"):
            qs = qs.filter(is_active=(active == "true"))

        data = [_product_to_dict(p) for p in qs]
        return JsonResponse(data, safe=False)

    if request.method == "POST":
        payload = _parse_json(request)
        if payload is None:
            return _json_error("Invalid JSON body.", 400)

        required = ["name", "producer_id", "category_id", "price"]
        missing = [k for k in required if k not in payload]
        if missing:
            return _json_error("Missing required fields.", 400, missing=missing)

        try:
            producer = Producer.objects.get(id=payload["producer_id"])
        except Producer.DoesNotExist:
            return _json_error("producer_id not found.", 404)

        try:
            category = Category.objects.get(id=payload["category_id"])
        except Category.DoesNotExist:
            return _json_error("category_id not found.", 404)

        try:
            price = Decimal(str(payload["price"]))
        except Exception:
            return _json_error("price must be a number.", 400)

        p = Product(
            producer=producer,
            category=category,
            name=payload["name"],
            description=payload.get("description", ""),
            unit=payload.get("unit", "each"),
            price=price,
            is_active=bool(payload.get("is_active", True)),
            is_organic=bool(payload.get("is_organic", False)),
            allergen_info=payload.get("allergen_info", ""),
            origin_notes=payload.get("origin_notes", ""),
        )
        # date fields (optional)
        for field in ("harvest_date", "best_before_date"):
            if payload.get(field):
                setattr(p, field, payload[field])

        try:
            p.full_clean()
            p.save()
        except Exception as e:
            return _json_error("Validation error.", 400, details=str(e))

        # optional inventory create
        inv_payload = payload.get("inventory")
        if isinstance(inv_payload, dict):
            inv = Inventory(product=p)
            if "stock_qty" in inv_payload:
                inv.stock_qty = int(inv_payload["stock_qty"])
            if inv_payload.get("available_from"):
                inv.available_from = inv_payload["available_from"]
            if inv_payload.get("available_to"):
                inv.available_to = inv_payload["available_to"]
            try:
                inv.full_clean()
                inv.save()
            except Exception as e:
                # rollback product if inventory fails
                p.delete()
                return _json_error("Inventory validation error.", 400, details=str(e))

        p = Product.objects.select_related("producer", "category").get(id=p.id)
        return JsonResponse(_product_to_dict(p), status=201)

    return HttpResponseNotAllowed(["GET", "POST"])


@csrf_exempt
def product_resource(request: HttpRequest, product_id: int):
    try:
        p = Product.objects.select_related("producer", "category").get(id=product_id)
    except Product.DoesNotExist:
        return _json_error("Product not found.", 404)

    if request.method == "GET":
        return JsonResponse(_product_to_dict(p))

    if request.method in ("PUT", "PATCH"):
        payload = _parse_json(request)
        if payload is None:
            return _json_error("Invalid JSON body.", 400)

        # allow changing these fields
        updatable = {
            "name", "description", "unit", "price", "is_active",
            "is_organic", "allergen_info", "origin_notes",
            "harvest_date", "best_before_date",
            "producer_id", "category_id",
            "inventory",
        }

        for key, value in payload.items():
            if key not in updatable:
                continue
            if key == "producer_id":
                try:
                    p.producer = Producer.objects.get(id=value)
                except Producer.DoesNotExist:
                    return _json_error("producer_id not found.", 404)
            elif key == "category_id":
                try:
                    p.category = Category.objects.get(id=value)
                except Category.DoesNotExist:
                    return _json_error("category_id not found.", 404)
            elif key == "price":
                try:
                    p.price = Decimal(str(value))
                except Exception:
                    return _json_error("price must be a number.", 400)
            elif key == "inventory" and isinstance(value, dict):
                inv, _ = Inventory.objects.get_or_create(product=p)
                if "stock_qty" in value:
                    inv.stock_qty = int(value["stock_qty"])
                if "available_from" in value:
                    inv.available_from = value["available_from"] or None
                if "available_to" in value:
                    inv.available_to = value["available_to"] or None
                try:
                    inv.full_clean()
                    inv.save()
                except Exception as e:
                    return _json_error("Inventory validation error.", 400, details=str(e))
            else:
                setattr(p, key, value)

        try:
            p.full_clean()
            p.save()
        except Exception as e:
            return _json_error("Validation error.", 400, details=str(e))

        p = Product.objects.select_related("producer", "category").get(id=p.id)
        return JsonResponse(_product_to_dict(p))

    if request.method == "DELETE":
        p.delete()
        return JsonResponse({"deleted": True, "id": product_id})

    return HttpResponseNotAllowed(["GET", "PUT", "PATCH", "DELETE"])
