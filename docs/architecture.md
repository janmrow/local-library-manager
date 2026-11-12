# Architecture

Django project `config` with apps `catalog`, `circulation`, `accounts` on one origin. Browser calls the same JSON API under `/api/v1/` that `pytest` exercises. PostgreSQL 17 holds app data and sessions. Table names are Django defaults (`catalog_bookcopy`, `circulation_loan`). Settings live in one `config/settings.py` driven by env; `APP_ENV` switches DB and logging.

`catalog` owns `Book` and `BookCopy`; `circulation` owns `Loan`; `accounts` owns `User` and `Librarians`. Transactions live in views and operations, never in `save()`. Slice tags: Read API → slice 1; accounts, session, and catalogue writes → slice 2; loan writes and return → slice 3; observability and OpenAPI → slice 4.

## Model

- `accounts.User(AbstractUser): pass`; `AUTH_USER_MODEL="accounts.User"`.
- `Book(title=CharField(255), author=CharField(255))`, `Meta.indexes=[Index(fields=["title","author"], name="catalog_book_search")]`.
- `BookCopy(inventory_code=CharField(max_length=24, unique=True), book=FK(catalog.Book, CASCADE, related_name="copies"))`; normalize in `save()`: trim to uppercase, validate `^[A-Za-z0-9-]{3,24}$`.
- `Loan(copy=FK(catalog.BookCopy, CASCADE), reader=FK(accounts.User, CASCADE), borrowed_at=DateTimeField(auto_now_add=True), returned_at=DateTimeField(null=True,blank=True))`, `UniqueConstraint(fields=["copy"], condition=Q(returned_at__isnull=True), name="unique_open_loan_per_copy")`. The `Loan` table ships in slice 1; writes are deferred to slice 3.
- `Librarians` group is created by data migration; demo accounts come from `seed_demo`.
- Availability is derived from copies minus open loans, never stored.

## Read API

- `GET /api/v1/books/` uses `PageNumberPagination`, `page_size=20`, `AllowAny`, `order_by("title","id")`, router in `config/urls.py`. Envelope is `{"count","next","previous","results":[{"id","title","author","available_copies","total_copies"}]}`.
- `q` matches title or author with `icontains`, ordered by title; empty or missing `q` returns all.
- `GET /api/v1/books/{id}/` returns the same object, no `copies[]`; unknown id returns `404 {"code":"not_found","detail":"..."}`.

## Write API

- Code normalize: trim, validate 3–24 ASCII `[A-Za-z0-9-]`, uppercase before save or lookup.
- Create book with first copy in one transaction; duplicate code rolls back both and returns `409 inventory_code_taken`.
- Checkout posts `{"inventory_code": "..."}`; success returns `201` with `Location: /api/v1/loans/{id}/`. Occupied copy returns `409 copy_unavailable` mapped after the atomic block rolls back.
- Errors use `{"code": "...", "detail": "..."}` for `400/403/404/409`.
- Scope: reader sees own loans only; out-of-scope loan ID returns `404`.
- `GET /api/v1/staff/loans/?inventory_code=`: returns zero or one open loan object, no pagination.
- Return posts to the loan ID once; retry returns the same `returned_at` with `200` and leaves a later loan of the same copy open.

## Checkout sequence

Browser `POST /api/v1/loans/` with session + CSRF → API checks access and code → DB inserts open loan. Available: commit → `201`. Occupied: unique violation → `409`. `X-Request-ID` links response to log.

## Session and CSRF

`GET /api/v1/session/` returns sign-in state and sets the CSRF cookie. Mutating calls send `X-CSRFToken`. Registration and sign-in enforce CSRF without a session. Re-read the cookie after sign-in rotates the token. Loan responses use `Cache-Control: no-store`.

## Observability

`X-Request-ID` middleware generates or propagates the ID, returns it on the response, and includes method, path, status, duration, and request ID in the server log. `config/settings.py` uses `ENGINE=django.db.backends.postgresql` from `DB_*` in `.env.example`; `pytest-django` uses `DJANGO_SETTINGS_MODULE=config.settings`.

## Frontend

Three server templates sharing one `api.js` fetch helper with CSRF handling. UI labels in Polish. Pages: public catalogue at `/` (`catalog/templates/catalog/book_list.html` + `static/js/api.js::apiGet`), librarian catalogue changes, reader checkout plus librarian return.
