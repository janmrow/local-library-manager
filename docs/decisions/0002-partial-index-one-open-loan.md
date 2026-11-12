# 0002 One open loan per copy in PostgreSQL

Date: 2026-11-12
Status: Accepted

## Context

Two parallel checkouts of the same copy must not both commit.

## Decision

Enforce with a partial unique index on open loans and map the known violation to `409 copy_unavailable` after rollback.

## Consequences

The database owns the rule under concurrency. App code translates the conflict; tests assert one `201`, one `409`, one committed loan.
