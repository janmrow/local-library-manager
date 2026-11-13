"""Loan endpoints (slice 3: checkout + scoped reads + staff lookup + return)."""

from django.db import IntegrityError, transaction
from django.http import Http404
from django.utils import timezone
from rest_framework import mixins, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from accounts.permissions import IsLibrarian, IsSignedIn
from accounts.views import enforce_csrf_without_session
from catalog.models import BookCopy
from catalog.serializers import normalize_code
from circulation.models import Loan
from circulation.serializers import CheckoutSerializer, LoanSerializer

NO_STORE = {"Cache-Control": "no-store"}
OPEN_LOAN_CONSTRAINT = "unique_open_loan_per_copy"


def loan_envelope(code: str, detail: str, status: int) -> Response:
    return Response({"code": code, "detail": detail}, status=status, headers=NO_STORE)


class LoanViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    """Caller-scoped loans: list shows the caller's open loans (bare array)."""

    permission_classes = [IsSignedIn]
    serializer_class = LoanSerializer

    def scoped_loans(self):
        return Loan.objects.filter(reader=self.request.user).select_related("copy")

    def get_queryset(self):
        queryset = self.scoped_loans().order_by("borrowed_at", "id")
        if self.action == "list":
            queryset = queryset.filter(returned_at__isnull=True)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(
            self.get_serializer(queryset, many=True).data, headers=NO_STORE
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            loan = self.get_object()
        except Http404:
            return loan_envelope("not_found", "Loan not found.", 404)
        return Response(self.get_serializer(loan).data, headers=NO_STORE)

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


class StaffLoanListView(APIView):
    """Librarian lookup of the open loan for one copy; always 200 [] or [loan]."""

    permission_classes = [IsLibrarian]

    def get(self, request):
        values = request.query_params.getlist("inventory_code")
        if len(values) > 1:
            return loan_envelope(
                "invalid", "Only one inventory_code is allowed.", 400
            )
        raw = values[0] if values else ""
        if not raw.strip():
            return loan_envelope("invalid", "inventory_code is required.", 400)
        try:
            code = normalize_code(raw)
        except serializers.ValidationError as exc:
            detail = exc.detail[0] if isinstance(exc.detail, list) else str(exc.detail)
            return loan_envelope("invalid", str(detail), 400)
        open_loan = (
            Loan.objects.filter(copy__inventory_code=code, returned_at__isnull=True)
            .select_related("copy")
            .first()
        )
        loans = [open_loan] if open_loan is not None else []
        return Response(LoanSerializer(loans, many=True).data, headers=NO_STORE)


class LoanReturnView(APIView):
    """Librarian return of one loan; retry returns the same returned_at."""

    permission_classes = [IsLibrarian]

    def post(self, request, pk):
        enforce_csrf_without_session(request)
        try:
            loan_id = int(pk)
        except (TypeError, ValueError):
            return loan_envelope("not_found", "Loan not found.", 404)
        try:
            with transaction.atomic():
                loan = (
                    Loan.objects.select_for_update()
                    .select_related("copy")
                    .get(pk=loan_id)
                )
                if loan.returned_at is None:
                    loan.returned_at = timezone.now()
                    loan.save(update_fields=["returned_at"])
        except Loan.DoesNotExist:
            return loan_envelope("not_found", "Loan not found.", 404)
        return Response(LoanSerializer(loan).data, headers=NO_STORE)
