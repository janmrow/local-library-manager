"""Circulation routes (slice 3 step 2: checkout + scoped reads)."""

from django.urls import path, re_path

from circulation.views import LoanViewSet

urlpatterns = [
    path(
        "loans/",
        LoanViewSet.as_view({"get": "list", "post": "create"}),
        name="loan-list",
    ),
    # Same pk pattern as the books router so garbage ids render JSON 404.
    re_path(
        r"^loans/(?P<pk>[^/.]+)/$",
        LoanViewSet.as_view({"get": "retrieve"}),
        name="loan-detail",
    ),
]
