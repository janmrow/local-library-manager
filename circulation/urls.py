"""Circulation routes (slice 3 step 1: checkout only)."""

from django.urls import path

from circulation.views import LoanViewSet

urlpatterns = [
    path("loans/", LoanViewSet.as_view({"post": "create"}), name="loan-list"),
]
