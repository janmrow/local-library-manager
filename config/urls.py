"""URL configuration (slice 3: catalogue + loans API + browse page)."""

from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from catalog.views import BookViewSet, api_not_found

router = DefaultRouter()
router.register(r"books", BookViewSet, basename="book")

urlpatterns = [
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("circulation.urls")),
    path("api/v1/", include(router.urls)),
    # Last among API routes: unmatched /api/v1/* stays a JSON 404.
    re_path(r"^api/v1/.*$", api_not_found),
    path("", include("catalog.page_urls")),
]
