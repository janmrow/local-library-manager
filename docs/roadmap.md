# Roadmap

Slice order is fixed. Each slice ends with a verifiable behaviour.

## 1. Catalogue slice

Goal: browse from DB to browser. Migrations, demo rows, `GET /api/v1/books/`, one page, `pytest` scenarios, one Playwright browse. Compare `curl -i`, DevTools, `SELECT` + `JOIN`.

Files: settings `config.settings` (`DJANGO_SETTINGS_MODULE=config.settings`); cmd `catalog/management/commands/seed_demo.py`; page `/` → `catalog/templates/catalog/book_list.html` + `static/js/api.js::apiGet`; pytest `tests/api/test_books.py`; Playwright `e2e/tests/catalogue.spec.ts` (`baseURL http://127.0.0.1:8001`).

Out: no `accounts` rows, session, or CSRF; no `POST` routes; no `staff/loans`; no OpenAPI or CI; no reader or librarian seed rows (`Loan` DDL only). After slice 1 consider minimal backend CI; browser job after the first E2E stabilizes.

Exit: `curl GET books` shows seeded rows, browse scenarios green (`pytest tests/api/test_books.py` + `catalogue.spec.ts`), harness repro green (fresh checkout, one API + one browser test, HTTP vs SQL).

## 2. Session and librarian catalogue

Goal: accounts and roles. Registration, sign-in, sign-out, `Librarians` group, librarian add book and copy. Check session cookie, CSRF on login, no DB write on refused access. Permission tests start at the first protected endpoint. Second Playwright flow.

## 3. Checkout and return

Goal: circulation by code. Validation unit tests, role and conflict API tests, concurrency `201` + `409` on real PostgreSQL with barrier sync and no sleeps, idempotent return incl. parallel returns and retry after re-loan. Third Playwright flow covering reader plus librarian return.

## 4. Local release

Goal: fresh-clone run, migrations, both CI jobs green, README accurate, OpenAPI published, one diagnosis note with HTTP, log, and DB evidence.

## Non-goals

No due dates or fines, no reservations, holds, or renewals, no ISBN import, no email activation or password reset, no full-text search (`icontains` only), no SPA (server templates + `api.js` only), no multi-branch support.
