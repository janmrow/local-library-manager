"""Circulation routes (slice 3: loans, staff lookup, return)."""

from django.urls import path, re_path

from circulation.views import LoanReturnView, LoanViewSet, StaffLoanListView

urlpatterns = [
    path(
        "loans/",
        LoanViewSet.as_view({"get": "list", "post": "create"}),
        name="loan-list",
    ),
    # [^/]+ (not the books router's [^/.]+) so dotted garbage ids also
    # reach the view and render JSON 404 instead of Django's HTML page.
    # NOTE: future loans/<segment>/ actions must be registered above
    # loan-detail, or [^/]+ will swallow the segment as pk.
    re_path(
        r"^loans/(?P<pk>[^/]+)/$",
        LoanViewSet.as_view({"get": "retrieve"}),
        name="loan-detail",
    ),
    re_path(
        r"^loans/(?P<pk>[^/]+)/return/$",
        LoanReturnView.as_view(),
        name="loan-return",
    ),
    path("staff/loans/", StaffLoanListView.as_view(), name="staff-loans"),
]
