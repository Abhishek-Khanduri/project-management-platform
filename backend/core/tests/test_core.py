from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.test import APIClient

from core.exceptions import api_exception_handler


def test_health_is_public():
    response = APIClient().get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_error_handler_wraps_http_errors():
    response = api_exception_handler(NotAuthenticated(), context={})

    assert response.status_code == 401
    assert response.data["error"]["code"] == "not_authenticated"


def test_error_handler_puts_field_errors_in_details():
    response = api_exception_handler(ValidationError({"title": ["Required."]}), context={})

    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"
    assert response.data["error"]["details"] == {"title": ["Required."]}
