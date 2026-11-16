"""Loan write operations (slice 3: transactions live here, not in save())."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from catalog.models import BookCopy, normalize_inventory_code
from circulation.models import Loan

OPEN_LOAN_CONSTRAINT = "unique_open_loan_per_copy"


class CopyNotFound(Exception):
    """Normalized code matches no copy."""


class CopyUnavailable(Exception):
    """Copy already has an open loan."""


def _is_open_loan_conflict(exc: IntegrityError) -> bool:
    """True when the error is the partial-unique-index violation.

    Checks the driver diagnostic (psycopg carries pgcode + constraint name on
    both __cause__ and __context__), falling back to the constraint name in
    the message. Anything else re-raises so unknown faults stay loud (500),
    never misreported as 409.
    """
    chained = (getattr(exc, "__cause__", None), getattr(exc, "__context__", None))
    for err in chained:
        diag = getattr(err, "diag", None)
        if getattr(diag, "constraint_name", None) == OPEN_LOAN_CONSTRAINT:
            return True
        if getattr(err, "pgcode", None) == "23505" and OPEN_LOAN_CONSTRAINT in str(
            err
        ):
            return True
    return OPEN_LOAN_CONSTRAINT in str(exc)


def checkout_loan(*, inventory_code: str, reader) -> Loan:
    """Insert one open loan; lookup and insert share a single atomic block.

    Normalizes defensively: HTTP callers already normalize via serializers,
    but direct callers must get the same match-or-404 contract.
    """
    try:
        code = normalize_inventory_code(inventory_code)
    except ValidationError:
        raise CopyNotFound from None
    with transaction.atomic():
        try:
            copy = BookCopy.objects.get(inventory_code=code)
        except BookCopy.DoesNotExist:
            raise CopyNotFound from None
        try:
            # Savepoint: on error roll back to here so the branch below
            # (exists check, re-raise) runs on a healthy transaction.
            with transaction.atomic():
                return Loan.objects.create(copy=copy, reader=reader)
        except IntegrityError as exc:
            if _is_open_loan_conflict(exc):
                raise CopyUnavailable from exc
            if not BookCopy.objects.filter(pk=copy.pk).exists():
                raise CopyNotFound from exc
            raise


def return_loan(*, loan_id: int) -> Loan | None:
    """Record the return once; a retry returns the unchanged row.

    Returns None when the loan does not exist. The row lock serializes
    parallel returns on the same loan.
    """
    with transaction.atomic():
        try:
            loan = (
                Loan.objects.select_for_update()
                .select_related("copy")
                .get(pk=loan_id)
            )
        except Loan.DoesNotExist:
            return None
        if loan.returned_at is None:
            loan.returned_at = timezone.now()
            loan.save(update_fields=["returned_at"])
        return loan
