# 0001 Django over FastAPI

Date: 2026-11-12
Status: Accepted

## Context

Single-branch circulation needs password accounts, server sessions, role separation, relational integrity, migrations, and a JSON API on the same origin with a small operational footprint. Candidates are Django with DRF versus FastAPI with a separate auth, session, and migration layer.

## Decision

Use Django 5.2 LTS with DRF for the app and API.

## Consequences

Sessions, password hashing, groups, and migrations come from the framework. Trade-off is a heavier stack in exchange for fewer custom security and migration paths and a standard LTS upgrade route.
