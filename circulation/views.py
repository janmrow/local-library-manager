"""Loan endpoints (slice 3: reader checkout; reads/staff/return land in later steps)."""

from django.db import IntegrityError
from rest_framework import mixins
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from accounts.permissions import IsSignedIn
from accounts.views import enforce_csrf_without_session
from catalog.models import BookCopy
from circulation.models import Loan
from circulation.serializers import CheckoutSerializer, LoanSerializer

NO_STORE = {"Cache-Control": "no-store"}
OPEN_LOAN_CONSTRAINT = "unique_open_loan_per_copy"


def loan_envelope(code: str, detail: str, status: int) -> Response:
    return Response({"code": code, "detail": detail}, status=status, headers=NO_STORE)


class LoanViewSet(mixins.CreateModelMixin, GenericViewSet):
    """Checkout only in step 1; list/retrieve arrive with scoping tests."""

    permission_classes = [IsSignedIn]
    serializer_class = LoanSerializer

    def create(self, request, *args, **kwargs):
        enforce_csrf_without_session(request)
        input_serializer = CheckoutSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        code = input_serializer.validated_data["inventory_code"]
        try:
            copy = BookCopy.objects.get(inventory_code=code)
        except BookCopy.DoesNotExist:
            return loan_envelope("not_found", "Unknown inventory_code.", 404)
        try:
            loan = input_serializer.save(copy=copy, reader=request.user)
        except IntegrityError as exc:
            diag = getattr(getattr(exc, "__cause__", None), "diag", None)
            if getattr(diag, "constraint_name", None) == OPEN_LOAN_CONSTRAINT:
                return loan_envelope(
                    "copy_unavailable", "Copy already has an open loan.", 409
                )
            if not BookCopy.objects.filter(pk=copy.pk).exists():
                return loan_envelope("not_found", "Unknown inventory_code.", 404)
            raise
        return Response(
            LoanSerializer(loan).data,
            status=201,
            headers={"Location": f"/api/v1/loans/{loan.id}/", **NO_STORE},
        )
