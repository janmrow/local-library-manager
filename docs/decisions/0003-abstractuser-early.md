# 0003 Custom user model early

Date: 2026-11-12
Status: Accepted

## Context

Changing the user model after the first migration is costly in Django.

## Decision

Set a minimal `AbstractUser` model before the first migration. Public registration grants reader access; staff rights come from the `Librarians` group.

## Consequences

Account identifier can evolve without a rebuild. Role checks stay at the API layer and in tests.
