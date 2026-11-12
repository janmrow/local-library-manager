"""Accounts routes (slice 2, step 1: session state only)."""

from django.urls import path

from accounts.views import SessionView

urlpatterns = [
    path("session/", SessionView.as_view(), name="session"),
]
