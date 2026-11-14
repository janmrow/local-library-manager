"""Slice 3: concurrency on real PostgreSQL (barrier sync, no sleeps)."""

import json
import threading
import traceback

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection, transaction
from django.utils import timezone
from django.test import Client

from accounts.permissions import LIBRARIANS_GROUP
from catalog.models import Book, BookCopy
from circulation.models import Loan
from tests.api.helpers import login


def run_parallel(count, worker):
    """Run worker(index, outcomes) on `count` threads; each gets its own connection."""
    barrier = threading.Barrier(count)
    outcomes, errors = {}, {}

    def wrap(index):
        try:
            worker(index, barrier, outcomes)
        except Exception:  # noqa: BLE001 - reraised below
            errors[index] = traceback.format_exc()
        finally:
            connection.close()

    threads = [
        threading.Thread(target=wrap, args=(i,), daemon=True)
        for i in range(count)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert not any(thread.is_alive() for thread in threads), "worker hung"
    assert not errors, f"worker errors: {errors!r}"
    return outcomes


@pytest.mark.django_db(transaction=True)
class TestLoanConcurrency:
    def test_parallel_checkout_commits_exactly_one_open_loan(self, db):
        users = get_user_model()
        users.objects.create_user(username="reader1", password="pass12345")
        users.objects.create_user(username="reader2", password="pass12345")
        book = Book.objects.create(title="Solaris", author="Stanisław Lem")
        copy = BookCopy.objects.create(book=book, inventory_code="LL-501")

        def checkout(index, barrier, outcomes):
            test_client = Client(enforce_csrf_checks=True)
            token = login(test_client, f"reader{index + 1}", "pass12345")
            barrier.wait(timeout=15)
            response = test_client.post(
                "/api/v1/loans/",
                data=json.dumps({"inventory_code": "LL-501"}),
                content_type="application/json",
                HTTP_X_CSRFTOKEN=token,
            )
            outcomes[index] = (response.status_code, response.json())

        results = run_parallel(2, checkout)
        bodies = {status: body for status, body in results.values()}
        assert sorted(bodies) == [201, 409]
        assert "code" not in bodies[201]
        assert bodies[409] == {
            "code": "copy_unavailable",
            "detail": "Copy already has an open loan.",
        }
        assert (
            Loan.objects.filter(copy=copy, returned_at__isnull=True).count() == 1
        )

    def test_parallel_returns_share_one_timestamp(self, db):
        users = get_user_model()
        reader = users.objects.create_user(username="reader1", password="pass12345")
        for i in (1, 2):
            librarian = users.objects.create_user(
                username=f"lib{i}", password="pass12345"
            )
            librarian.groups.add(
                Group.objects.get_or_create(name=LIBRARIANS_GROUP)[0]
            )
        book = Book.objects.create(title="Solaris", author="Stanisław Lem")
        copy = BookCopy.objects.create(book=book, inventory_code="LL-502")
        loan = Loan.objects.create(copy=copy, reader=reader)

        def return_loan(index, barrier, outcomes):
            test_client = Client(enforce_csrf_checks=True)
            token = login(test_client, f"lib{index + 1}", "pass12345")
            barrier.wait(timeout=15)
            response = test_client.post(
                f"/api/v1/loans/{loan.id}/return/",
                data=json.dumps({}),
                content_type="application/json",
                HTTP_X_CSRFTOKEN=token,
            )
            outcomes[index] = (response.status_code, response.json()["returned_at"])

        outcomes = run_parallel(2, return_loan)
        assert [status for status, _ in outcomes.values()] == [200, 200]
        stamps = {stamp for _, stamp in outcomes.values()}
        assert len(stamps) == 1
        loan.refresh_from_db()
        assert loan.returned_at is not None

    # End-state only: asserts the checkout succeeds and leaves exactly one
    # open loan, not that the POST actually blocked on the row lock.
    def test_checkout_succeeds_after_concurrent_return(self, db):
        reader = get_user_model().objects.create_user(
            username="reader1", password="pass12345"
        )
        book = Book.objects.create(title="Solaris", author="Stanisław Lem")
        copy = BookCopy.objects.create(book=book, inventory_code="LL-503")
        loan = Loan.objects.create(copy=copy, reader=reader)
        held = {}

        # ORM (not HTTP): the view commits per request, so only direct ORM
        # access can hold the row lock open across the barrier.
        def returner(index, barrier, outcomes):
            with transaction.atomic():
                locked = Loan.objects.select_for_update().get(pk=loan.pk)
                held["saw_open"] = locked.returned_at is None
                barrier.wait(timeout=15)
                locked.returned_at = timezone.now()
                locked.save(update_fields=["returned_at"])

        def borrower(index, barrier, outcomes):
            test_client = Client(enforce_csrf_checks=True)
            token = login(test_client, "reader1", "pass12345")
            barrier.wait(timeout=15)
            response = test_client.post(
                "/api/v1/loans/",
                data=json.dumps({"inventory_code": "LL-503"}),
                content_type="application/json",
                HTTP_X_CSRFTOKEN=token,
            )
            outcomes[index] = (response.status_code, response.json())

        def worker(index, barrier, outcomes):
            (returner if index == 0 else borrower)(index, barrier, outcomes)

        outcomes = run_parallel(2, worker)
        assert held["saw_open"] is True
        assert outcomes[1][0] == 201
        assert "code" not in outcomes[1][1]
        open_loans = Loan.objects.filter(returned_at__isnull=True)
        assert open_loans.count() == 1
        assert open_loans.get().pk != loan.pk
