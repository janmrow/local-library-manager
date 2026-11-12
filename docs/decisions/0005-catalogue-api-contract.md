# 0005 Catalogue API contract

Date: 2026-11-12
Status: Accepted
Amended: 2026-11-12 — staff lookup is `[]`/`[loan]` with `200`.

## Context

Slice 1 needs fixed response shapes so pytest, UI, and docs assert the same contract. Open points were list fields, search semantics, error envelope, `Location`, and the staff loan lookup shape.

## Decision

List and detail share `id`, `title`, `author`, `available_copies`, `total_copies`. Search `q` is `icontains` on title and author ordered by title. Errors are `{"code": "...", "detail": "..."}` with `copy_unavailable` and `inventory_code_taken`. Success `Location` is the path `/api/v1/loans/{id}/`. Staff lookup always returns an array with `200`: `[]` or `[loan]`, without pagination.

## Consequences

Contract tests assert field names, search order, error codes, and the `Location` path. Changing any of these is a contract change with schema, examples, and tests updated together.
