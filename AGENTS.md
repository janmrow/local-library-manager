# AGENTS.md

## Project

Local Library Manager for one library branch. Django 5.2 LTS, DRF, PostgreSQL 17. Same origin serves HTML and JSON API at `/api/v1/`. UI labels in Polish, contract and docs in English.

## Map — read conditionally

- Scope, API, commands: `README.md` — only for run, API, or command tasks
- Process, branches, PR, diagnosis: `CONTRIBUTING.md` — only for commit, PR, or diagnosis tasks
- Local settings: `.env.example` — only when running DB or app
- Data model and write rules: `docs/architecture.md` — on model, shape, or schema changes
- Slices and order: `docs/roadmap.md` — when planning a slice
- Rationale: `docs/decisions/` — when touching the decided area

## Commands

Use `README.md` commands as source. Run the focused test while iterating; on code or contract changes finish with full `pytest` plus `makemigrations --check --dry-run` (docs-only: skip). Keep `uv.lock` and `e2e/package-lock.json` current (when present in repo).

## Boundaries

- Django project `config` with apps `catalog`, `circulation`, `accounts` and DRF. Serializers own the contract, permissions own access, transactions stay with the operation.
- `Librarians` group for staff. Public registration grants reader access. Scope loan reads to the caller. Enforce writes in the API.
- CSRF explicit on registration and session views, including logged-out requests. API CSRF rejections are JSON. No credentials, cookies, or personal data in logs or artifacts. Playwright traces stay local (gitignored); never paste raw traces in PRs — only redacted excerpts. Use synthetic accounts only.

## Data rules

- `inventory_code`: trim → validate 3–24 ASCII `[A-Za-z0-9-]` on the trimmed input, before uppercase → uppercase, one shared function for writes and lookups; unique in PostgreSQL.
- Book with first copy is atomic. Open loan means `returned_at IS NULL`. One open loan per copy via partial unique index; map the known violation to `409` after rollback.
- Return sets `returned_at` once per loan ID; retry preserves the timestamp and leaves a later loan intact.
- Migrations ship with model changes. Route, status, shape, role, or constraint change is a contract change: update schema, examples, and tests together.

## Done

- One observable behaviour per change. State actor, initial data, request, expected response, expected DB state first.
- Transactional tests for commits and concurrency with separate connections. No timing sleeps. Gates per slice are defined in `CONTRIBUTING.md`.
- Report per `CONTRIBUTING.md` PR and failure-note format (concise English).

## Guardrails

- Always: read files, run relevant checks, confirm important results via HTTP, SQL, or trace.
- Ask first: deletions, migrations, schema changes, new dependencies.
- Never: direct-push to main, commit secrets or `.env`, write to prod.
