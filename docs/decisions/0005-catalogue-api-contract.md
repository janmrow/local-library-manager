# 0005 Catalogue API contract

Date: 2026-11-12
Status: Accepted

## Context

Slice 1 needs fixed response shapes so pytest, UI, and docs assert the same contract. Open points were list fields, search semantics, error envelope, `Location`, and the staff loan lookup shape.

## Decision

List and detail share `id`, `title`, `author`, `available_copies`, `total_copies`. Search `q` is `icontains` on title and author ordered by title. Errors are `{"code": "...", "detail": "..."}` with `copy_unavailable` and `inventory_code_taken`. Success `Location` is the path `/api/v1/loans/{id}/`. Staff lookup returns zero or one open loan object without pagination.

## Consequences

Contract tests assert field names, search order, error codes, and the `Location` path. Changing any of these is a contract change with schema, examples, and tests updated together.
