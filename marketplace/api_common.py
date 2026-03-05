import json
from typing import Any, Dict, Optional

from django.http import HttpRequest, JsonResponse


def json_error(message: str, status: int = 400, **extra) -> JsonResponse:
    payload: Dict[str, Any] = {"error": message}
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=status)


def parse_json(request: HttpRequest) -> Optional[Dict[str, Any]]:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return None
