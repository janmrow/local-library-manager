"""Accounts routes (slice 2, step 2: registration added)."""

from django.urls import path

from accounts.views import RegistrationView, SessionView

urlpatterns = [
    path("accounts/", RegistrationView.as_view(), name="accounts"),
    path("session/", SessionView.as_view(), name="session"),
]
