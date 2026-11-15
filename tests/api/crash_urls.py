"""Test-only URLconf: a crashing view for the request-id 500 path."""

from django.urls import path


def boom(request):
    raise RuntimeError("boom")


urlpatterns = [path("boom/", boom)]
