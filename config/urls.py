"""URL configuration (slice 1: catalogue read API + browse page)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from catalog.views import BookViewSet

router = DefaultRouter()
router.register(r"books", BookViewSet, basename="book")

urlpatterns = [
    path("api/v1/", include(router.urls)),
    path("", include("catalog.page_urls")),
]
