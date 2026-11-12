# Contributing

## Branches

- `main` is protected. Direct push to `main` is forbidden; landing only via the rebase-merge button.
- Work in short-lived branches from up-to-date `main`: `feat/<kebab>`, `fix/<kebab>`, `test/<kebab>`, `chore/<kebab>`, `docs/<kebab>`. Example: `feat/catalogue-browse`, `fix/loan-409-on-retry`. Update the branch with rebase; no merge commits on branches.
- One observable behaviour per branch; prefer a single commit per PR (fixups via `git commit --amend`). With several commits, each follows the subject format; the PR title describes the whole change.

## Commits

- Conventional Commits in English: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- Subject: `<type>: <imperative verb + what>`, max 72 chars, no scope, e.g. `feat: add catalogue search by author`. Code, tests, and docs may land as separate commits of matching types; fixups go through `git commit --amend`.

## Pull requests

- Title uses commit subject format, e.g. `feat: add catalogue search by author`.
- Body order: 1. Changed 2. Why 3. Slice (`n/a` for docs-only) + contract-change yes/no 4. Verification (commands + results) 5. Gaps. Contract change must list schema + examples + tests touched.
- Gates (run from root): `uv run --locked --env-file .env pytest`, `uv run --locked --env-file .env python manage.py makemigrations --check --dry-run`, `git diff --exit-code uv.lock e2e/package-lock.json`. Run full `npx playwright test` in `e2e/` if UI, routes, or any slice-1/2/3 flow changed; otherwise state why skipped. No pre-commit or CI yet: paste gate outputs in PR body.
- Slice gates: slice-1 gate is one pytest + one Playwright; full permission matrix + concurrency `201`/`409` are slice-3 gates; three flows + lockfiles + `makemigrations --check` are slice-4 release gates.
- Merge: rebase via GitHub, branch deleted after merge. Solo: author merges after self-review checklist + green gates. With collaborators: one approving review required (enforced in GitHub settings, not here).
- Failure report: expected vs observed, evidence (request ID, log, SQL), likely layer, next check.

## Local verification

- Follow `README.md` run and test commands. No app code yet: do not invent commands.
- Tests live in `tests/unit/`, `tests/api/`, `tests/integration/`. Deps are Django, DRF, psycopg, drf-spectacular, pytest plus pytest-django.
- Slice-1 seed (rerunnable via `get_or_create`): `Book("Solaris","Stanisław Lem")` + copy `LL-001` (available) + 1 second book; `?q=lem` must hit Solaris. Reader/librarian accounts arrive with slice 2.
- Give each test its own data. Concurrency check uses two independent signed-in clients and asserts one `201`, one `409`, one committed open loan.

## Diagnosis

- Follow `X-Request-ID` from response to server log, then check loan rows in PostgreSQL.
- Note format: `Expected and observed / Evidence / Likely layer / Next action`.
- Keep credentials, cookies, and personal fields out of logs and artifacts.
