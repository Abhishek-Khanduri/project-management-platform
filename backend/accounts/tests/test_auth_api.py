import pytest
from django.contrib.auth import get_user_model

from conftest import PASSWORD

pytestmark = pytest.mark.django_db


def login(api_client, email="alice@example.com"):
    return api_client.post("/api/auth/login/", {"email": email, "password": PASSWORD})


def test_register_creates_user_with_hashed_password(api_client):
    response = api_client.post(
        "/api/auth/register/",
        {"email": "Bob@Example.com", "password": PASSWORD, "first_name": "Bob"},
    )

    assert response.status_code == 201
    assert "password" not in response.json()
    user = get_user_model().objects.get(email="bob@example.com")
    assert user.password != PASSWORD
    assert user.check_password(PASSWORD)


def test_register_rejects_duplicate_email(api_client, make_user):
    make_user("bob@example.com")

    response = api_client.post("/api/auth/register/", {"email": "bob@example.com", "password": PASSWORD})

    assert response.status_code == 400
    assert "email" in response.json()["error"]["details"]


def test_register_rejects_weak_password(api_client):
    response = api_client.post("/api/auth/register/", {"email": "bob@example.com", "password": "123"})

    assert response.status_code == 400
    assert "password" in response.json()["error"]["details"]


def test_login_returns_access_and_refresh_tokens(api_client, make_user):
    make_user()

    response = login(api_client)

    assert response.status_code == 200
    assert {"access", "refresh"} <= response.json().keys()


def test_login_with_wrong_password_fails(api_client, make_user):
    make_user()

    response = api_client.post("/api/auth/login/", {"email": "alice@example.com", "password": "wrong"})

    assert response.status_code == 401


def test_protected_endpoint_requires_token(api_client):
    response = api_client.get("/api/auth/me/")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_me_returns_current_user_with_valid_token(api_client, make_user):
    make_user()
    access = login(api_client).json()["access"]

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = api_client.get("/api/auth/me/")

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_invalid_token_is_rejected(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")

    response = api_client.get("/api/auth/me/")

    assert response.status_code == 401


def test_refresh_returns_new_access_token(api_client, make_user):
    make_user()
    refresh = login(api_client).json()["refresh"]

    response = api_client.post("/api/auth/refresh/", {"refresh": refresh})

    assert response.status_code == 200
    assert "access" in response.json()


def test_logout_blacklists_refresh_token(api_client, make_user):
    make_user()
    tokens = login(api_client).json()
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    logout = api_client.post("/api/auth/logout/", {"refresh": tokens["refresh"]})
    refresh_after_logout = api_client.post("/api/auth/refresh/", {"refresh": tokens["refresh"]})

    assert logout.status_code == 204
    assert refresh_after_logout.status_code == 401
