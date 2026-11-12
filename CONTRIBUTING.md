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
- Body uses Markdown headings in this order: `## Changed`, `## Why`, `## Slice / Contract`, `## Verification`, `## Gaps`. Contract change must list schema + examples + tests touched.
- Gates (run from root): `uv run --locked --env-file .env pytest`, `uv run --locked --env-file .env python manage.py makemigrations --check --dry-run`, `git diff --exit-code -- uv.lock e2e/package-lock.json` (only when the files exist; missing before the first deps is not a fail). Consistency via `uv sync --locked` and `npm ci`; review lockfile diffs together with manifests. Run full `npx playwright test` in `e2e/` if UI, routes, or any slice-1/2/3 flow changed; otherwise state why skipped. No pre-commit or CI yet: paste gate outputs under `## Verification`.
- Slice gates:
  - Slice 1: browse scenarios (`pytest` + Playwright browse + `curl` vs SQL) + fresh-checkout harness repro. OpenAPI is explicitly deferred to slice 4.
  - Slice 2: permission tests at the first protected endpoint + second Playwright flow.
  - Slice 3: full permission matrix + concurrency `201`/`409` (separate connections, no sleeps) + idempotent return + third flow.
  - Slice 4: three flows + lockfiles + `makemigrations --check` + OpenAPI + diagnosis note.
- Merge: rebase via GitHub, branch deleted after merge. Solo: author merges after self-review checklist + green gates. With collaborators: one approving review required (enforced in GitHub settings, not here).
- Handoff for an interrupted slice: leave a note in the existing issue — state, last verification, blocker, next step. No parallel plan system; no `CLAUDE.md` duplicate (`AGENTS.md` is the entry).
- Failure report: expected vs observed, evidence (request ID, log, SQL), likely layer, next check.

## Local verification

- Follow `README.md` run and test commands. No app code yet: do not invent commands.
- Tests live in `tests/unit/`, `tests/api/`, `tests/integration/`. Deps are Django, DRF, psycopg, drf-spectacular, pytest plus pytest-django.
- Slice-1 seed (rerunnable via `get_or_create`): `Book("Solaris","Stanisław Lem")` + copy `LL-001` (available) + 1 second book; `?q=lem` must hit Solaris. Reader/librarian accounts arrive with slice 2.
- Give each test its own data. Concurrency check uses two independent signed-in clients with separate connections and barrier sync (no sleeps) and asserts one `201`, one `409`, one committed open loan.
- Return check covers parallel returns and retry of an old loan after re-loan.

## Diagnosis

- Follow `X-Request-ID` from response to server log, then check loan rows in PostgreSQL.
- Note format: `Expected and observed / Evidence / Likely layer / Next action`.
- Keep credentials, cookies, and personal fields out of logs and artifacts. Traces stay local (gitignored); in PRs attach only redacted excerpts, never raw traces.
