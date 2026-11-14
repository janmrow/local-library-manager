"""Shared API test helpers (CSRF client, login, demo roles)."""

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client

from accounts.permissions import LIBRARIANS_GROUP


def csrf_client():
    return Client(enforce_csrf_checks=True)


def get_token(test_client):
    response = test_client.get("/api/v1/session/")
    assert response.status_code == 200
    return response.cookies["csrftoken"].value


def login(test_client, username="reader1", password="pass12345"):
    token = get_token(test_client)
    response = test_client.post(
        "/api/v1/session/",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200
    return response.cookies["csrftoken"].value


def make_librarian(username="lib1", password="pass12345"):
    user = get_user_model().objects.create_user(username=username, password=password)
    group, _ = Group.objects.get_or_create(name=LIBRARIANS_GROUP)
    user.groups.add(group)
    return user
