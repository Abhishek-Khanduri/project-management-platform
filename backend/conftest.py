"""Shared pytest fixtures, available to every test file."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

PASSWORD = "Str0ng-pass-123"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make_user(email="alice@example.com"):
        return get_user_model().objects.create_user(username=email, email=email, password=PASSWORD)

    return _make_user


@pytest.fixture
def auth_client(make_user):
    """Returns a function that gives an APIClient logged in as the given user."""

    def _auth_client(user=None):
        user = user or make_user()
        client = APIClient()
        client.force_authenticate(user)
        return client

    return _auth_client
