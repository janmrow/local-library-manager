# Diagnosis: second checkout of the same copy returns 409

Case: a signed-in reader checks out `LL-001` twice in a row (the second
request uses `"  ll-001 "` to also exercise code normalization).
Fresh demo database, dev server on `127.0.0.1:8000`.

## Expected and observed

Expected: first checkout commits (`201` + `Location`), second checkout is
refused with `409 {"code":"copy_unavailable"}` and no new loan row.

Observed: exactly that. No bug — the note pins the evidence chain
(response → `X-Request-ID` → server log → loan rows) for the slice-4 release.

## Evidence

HTTP (response headers trimmed to the relevant fields):

```http
POST /api/v1/loans/ {"inventory_code":"LL-001"}
→ 201 Created
  Location: /api/v1/loans/1/
  X-Request-ID: 36a4c724-2a4a-485f-b5f1-7f31356b95f0
  {"id":1,"inventory_code":"LL-001","book":1,"borrowed_at":"...","returned_at":null}

POST /api/v1/loans/ {"inventory_code":"  ll-001 "}
→ 409 Conflict
  X-Request-ID: c5d96067-0b91-4e1f-9522-4d076da5f29c
  {"code":"copy_unavailable","detail":"Copy already has an open loan."}
```

Server log (matched by request ID):

```text
POST /api/v1/loans/ 201 15.4ms rid=36a4c724-2a4a-485f-b5f1-7f31356b95f0
POST /api/v1/loans/ 409 11.5ms rid=c5d96067-0b91-4e1f-9522-4d076da5f29c
```

PostgreSQL after both requests:

```sql
SELECT c.inventory_code, l.id, l.borrowed_at, l.returned_at
FROM catalog_bookcopy AS c
LEFT JOIN circulation_loan AS l ON l.copy_id = c.id
WHERE c.inventory_code = 'LL-001'
ORDER BY l.borrowed_at DESC;
```

```text
 inventory_code | id |          borrowed_at          | returned_at
----------------+----+-------------------------------+-------------
 LL-001         |  1 | 2026-11-15 20:08:57.435259+00 |
```

One row, `returned_at IS NULL`: exactly one open loan — the `201` committed,
the `409` wrote nothing.

## Likely layer

Database + operation mapping, working as designed: the partial unique index
`unique_open_loan_per_copy` rejects the second insert, `checkout_loan`
rolls the savepoint back and maps the violation to `409 copy_unavailable`.
Normalization (`"  ll-001 "` → `LL-001`) hit the same copy, confirming the
409 is about the copy, not the input shape.

## Next action

None (no fault). If a client loses the `201` response, it reconciles via
`GET /api/v1/loans/` (caller's open loans). A librarian closes the loan with
`POST /api/v1/loans/1/return/`; a retry returns the same `returned_at`.
