from __future__ import annotations

from typing import Any, Dict

from django.db import IntegrityError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .api_common import json_error, parse_json
from .api_serializers import customer_to_dict
from .models import Customer


@csrf_exempt
def customers_collection(request: HttpRequest):
    if request.method == "GET":
        qs = Customer.objects.all().order_by("id")
        # filters
        active = request.GET.get("active")
        email = request.GET.get("email")
        postcode = request.GET.get("postcode")
        if active in ("true", "false"):
            qs = qs.filter(is_active=(active == "true"))
        if email:
            qs = qs.filter(email__iexact=email)
        if postcode:
            qs = qs.filter(postcode__iexact=postcode)

        return JsonResponse([customer_to_dict(x) for x in qs], safe=False)

    if request.method == "POST":
        payload = parse_json(request)
        if payload is None:
            return json_error("Invalid JSON body.", 400)

        required = ["full_name", "email", "postcode"]
        missing = [k for k in required if k not in payload]
        if missing:
            return json_error("Missing required fields.", 400, missing=missing)

        try:
            obj = Customer.objects.create(
                full_name=str(payload["full_name"]).strip(),
                email=str(payload["email"]).strip().lower(),
                phone=str(payload.get("phone", "")).strip(),
                postcode=str(payload["postcode"]).strip(),
                is_active=bool(payload.get("is_active", True)),
            )
        except IntegrityError:
            return json_error("Customer with this email already exists.", 409)

        return JsonResponse(customer_to_dict(obj), status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def customer_resource(request: HttpRequest, customer_id: int):
    try:
        obj = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        return json_error("Customer not found.", 404)

    if request.method == "GET":
        return JsonResponse(customer_to_dict(obj))

    if request.method in ("PUT", "PATCH"):
        payload = parse_json(request)
        if payload is None:
            return json_error("Invalid JSON body.", 400)

        # For PUT, treat as full update of editable fields
        fields = ["full_name", "email", "phone", "postcode", "is_active"]
        if request.method == "PUT":
            missing = [k for k in ("full_name", "email", "postcode") if k not in payload]
            if missing:
                return json_error("Missing required fields for PUT.", 400, missing=missing)

        for f in fields:
            if f in payload:
                if f == "email":
                    setattr(obj, f, str(payload[f]).strip().lower())
                elif f in ("full_name", "phone", "postcode"):
                    setattr(obj, f, str(payload[f]).strip())
                elif f == "is_active":
                    setattr(obj, f, bool(payload[f]))

        try:
            obj.save()
        except IntegrityError:
            return json_error("Customer with this email already exists.", 409)

        return JsonResponse(customer_to_dict(obj))

    if request.method == "DELETE":
        obj.delete()
        return JsonResponse({"deleted": True})

    return JsonResponse({"error": "Method not allowed"}, status=405)
