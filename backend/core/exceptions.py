"""
One place that turns every error into the same JSON shape:

    {"error": {"code": "not_found", "message": "Not found.", "details": {...}}}
"""
import logging

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class Conflict(APIException):
    """409: the request clashes with the current state (e.g. user is already a member)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict with the current state of the resource."
    default_code = "conflict"


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    # Not a DRF/HTTP error, so it is a bug: log it and hide the details.
    if response is None:
        logger.exception("Unhandled error in %s", context["view"].__class__.__name__)
        return Response(
            {"error": {"code": "server_error", "message": "Something went wrong.", "details": {}}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        error = {"code": "validation_error", "message": "Invalid input.", "details": response.data}
    else:
        code = getattr(exc, "default_code", "error")
        message = response.data.get("detail", str(exc)) if isinstance(response.data, dict) else str(exc)
        error = {"code": code, "message": str(message), "details": {}}

    response.data = {"error": error}
    return response
