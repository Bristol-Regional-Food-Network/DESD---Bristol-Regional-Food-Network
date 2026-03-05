from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt

from .api_common import json_error, parse_json
from .api_serializers import inventory_to_dict
from .models import Inventory, Product


@csrf_exempt
def product_inventory_resource(request: HttpRequest, product_id: int):
    """GET/PUT/PATCH inventory for a product. Creates inventory row on demand."""
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return json_error("Product not found.", 404)

    inv, _created = Inventory.objects.get_or_create(product=product)

    if request.method == "GET":
        return JsonResponse(inventory_to_dict(inv))

    if request.method in ("PUT", "PATCH"):
        payload = parse_json(request)
        if payload is None:
            return json_error("Invalid JSON body.", 400)

        # For PUT, require at least stock_qty presence
        if request.method == "PUT":
            if "stock_qty" not in payload:
                return json_error("Missing required field for PUT.", 400, missing=["stock_qty"])

        if "stock_qty" in payload:
            try:
                inv.stock_qty = int(payload["stock_qty"])
            except (TypeError, ValueError):
                return json_error("stock_qty must be an integer.", 400)

        if "available_from" in payload:
            inv.available_from = parse_date(payload["available_from"]) if payload["available_from"] else None
        if "available_to" in payload:
            inv.available_to = parse_date(payload["available_to"]) if payload["available_to"] else None

        try:
            inv.full_clean()
            inv.save()
        except Exception as e:
            return json_error("Invalid inventory data.", 400, details=str(e))

        return JsonResponse(inventory_to_dict(inv))

    return JsonResponse({"error": "Method not allowed"}, status=405)
