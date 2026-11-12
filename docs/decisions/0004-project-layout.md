# 0004 Project layout

Date: 2026-11-12
Status: Accepted

## Context

Agent work needs a fixed home for models, settings, and users. `README` SQL already uses `catalog_bookcopy` and `circulation_loan`. Options were one `library` app, `catalog` + `circulation`, or that pair plus `accounts`.

## Decision

Use Django project `config` with apps `catalog`, `circulation`, `accounts`. Keep Django default table names. Put the custom `AbstractUser` in `accounts`. Use one `config/settings.py` driven by env; `APP_ENV` switches DB and logging.

## Consequences

Models, migrations, and tests have a fixed place. No custom `db_table`. Settings stay minimal until e2e or prod forces a split.
