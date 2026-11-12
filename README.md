# Local Library Manager

> Planning draft. The routes and commands below describe the intended first release. The route table is the release target — do not implement ahead: per-slice scope is in `docs/roadmap.md`. Slice 1 builds only `GET books/` rows. Full table accuracy is verified in slice 4.

Local Library Manager is a small circulation app for a single library branch. Visitors can browse the catalogue. Readers can create an account, sign in and check out the copy they have in hand by entering its inventory code. A librarian can add books and copies and record returns at the desk.

## Working with agents

Agents read [AGENTS.md](AGENTS.md) first, then [CONTRIBUTING.md](CONTRIBUTING.md). Follow the conditional map inside `AGENTS.md`.

## Architecture

Django + DRF + PostgreSQL 17 on one origin; the browser uses the JSON API. Details (models, shapes, rules): `docs/architecture.md`.

## Run on Ubuntu

Install `uv`, Docker with Compose, and Node.js 24 for browser tests. From the repository root, start the database, apply migrations and load synthetic demo records.

```bash
cp .env.example .env
docker compose up -d --wait db
uv sync --locked
uv run --locked --env-file .env python manage.py migrate
uv run --locked --env-file .env python manage.py seed_demo
uv run --locked --env-file .env python manage.py runserver 127.0.0.1:8000
```

Open <http://127.0.0.1:8000/>. The demo dataset includes available and checked-out copies and local reader and librarian accounts. The seed command can be rerun on a demo database. Use `.env.example` to see the local settings and keep your own `.env` outside version control.

## API

The generated OpenAPI document is at `/api/schema/`. The application uses Django session cookies. Read `/api/v1/session/` to obtain the CSRF cookie. Include the current token in `X-CSRFToken` on requests that write data, including account creation and sign-in. Read the cookie again after sign-in rotates the token.

| Method and path | Who | Result |
| --- | --- | --- |
| `GET /api/v1/books/?q=lem` | Anyone | Paginated catalogue with available copy counts. Search matches title or author. |
| `GET /api/v1/books/{id}/` | Anyone | One catalogue record with its current availability. |
| `POST /api/v1/accounts/` | Anyone with valid CSRF | Creates a reader account from a username and password. Returns `201`. |
| `GET /api/v1/session/` | Anyone | Returns current sign-in state and sets the CSRF cookie. |
| `POST /api/v1/session/` | Anyone with valid CSRF | Signs in with username and password. Returns `200`. |
| `DELETE /api/v1/session/` | Signed-in user | Signs out. Returns `204`. |
| `POST /api/v1/books/` | Librarian | Creates a catalogue record and its first copy in one transaction. Returns `201`. |
| `POST /api/v1/books/{id}/copies/` | Librarian | Adds a physical copy to an existing catalogue record. Returns `201`. |
| `GET /api/v1/loans/` | Signed-in user | Lists the caller's open loans. |
| `GET /api/v1/loans/{id}/` | Loan owner | Reads one of the caller's loans. Returns `404` for a missing loan or a loan outside that scope. |
| `POST /api/v1/loans/` | Signed-in user | Checks out a copy by inventory code. Returns `201` and the loan location. |
| `GET /api/v1/staff/loans/?inventory_code=LL-001` | Librarian | Finds the open loan for that copy. Returns `200` with `[]` or `[loan]`. |
| `POST /api/v1/loans/{id}/return/` | Librarian | Records the return of that loan. A retry returns the same `returned_at` with `200`. |

```bash
curl -i 'http://127.0.0.1:8000/api/v1/books/?q=lem'
```

A checkout takes `{"inventory_code":"LL-001"}`. Expect `400` for an invalid request, `403` for a refused session, CSRF or permission check, `404` for an unknown copy, and `409` with `copy_unavailable` when the copy already has an open loan. A lost checkout response can be reconciled by reading the caller's open loans.

Catalogue creation takes `title`, `author` and `inventory_code`. Adding another copy takes just `inventory_code`. A duplicate code on either catalogue write returns `409` with `inventory_code_taken`.

## Run the tests

```bash
uv run --locked --env-file .env pytest
uv run --locked --env-file .env python manage.py makemigrations --check --dry-run
```

pytest covers validation, the API contract, permissions and PostgreSQL behaviour. The concurrency contract (two independent signed-in clients, one `201`, one `409`, one committed loan) is defined in `CONTRIBUTING.md`.

Create the browser test database once and run the Chromium tests from `e2e/`.

```bash
docker compose exec -T db createdb -U library library_e2e
DB_NAME=library_e2e APP_ENV=e2e uv run --locked --env-file .env python manage.py migrate
DB_NAME=library_e2e APP_ENV=e2e uv run --locked --env-file .env python manage.py seed_demo
export UV_ENV_FILE="$PWD/.env"
cd e2e
npm ci
npx playwright install --with-deps chromium
npx playwright test
```

Playwright starts its own app instance on port 8001 against `library_e2e`. Its three workflows cover public browsing, librarian catalogue changes, and reader checkout followed by a librarian return. GitHub Actions runs the backend and browser checks in independent PostgreSQL environments and retains the Playwright trace on failure. Traces may contain cookies and network snapshots, so use synthetic accounts only and check trace content before publishing; keep retention short.

## Diagnose a failed checkout

Follow the diagnosis procedure in `CONTRIBUTING.md`: match the network response to the server log by `X-Request-ID`. Compare the expected result with the actual loan rows in PostgreSQL.

```sql
SELECT c.inventory_code, l.id, l.borrowed_at, l.returned_at
FROM catalog_bookcopy AS c
LEFT JOIN circulation_loan AS l ON l.copy_id = c.id
WHERE c.inventory_code = 'LL-001'
ORDER BY l.borrowed_at DESC;
```

The response, log and database state should explain the same outcome. File the failure note per `CONTRIBUTING.md`.
