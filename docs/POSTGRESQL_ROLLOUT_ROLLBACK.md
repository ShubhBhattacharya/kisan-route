# PostgreSQL rollout and rollback runbook

This runbook applies to isolated staging only. Do not point staging at production.

## Current verified state

- The application accepts PostgreSQL through `SUPABASE_DB_URL`, `KISAN_ROUTE_DATABASE_URL`, or `DATABASE_URL`.
- On Vercel, the app requires an explicit session secret and a persistent PostgreSQL URL; it refuses to fall back to local SQLite.
- Guardian storage is implemented with SQLAlchemy relational tables.
- Unit tests use SQLite in-memory; a real Supabase PostgreSQL connection and migration have not yet been run.
- The staging project exists separately from the original production project. Its database is not yet verified as connected to the app.

## 1. Configure staging secrets

In the staging Vercel Preview environment (or a dedicated staging Vercel project), set:

- `DATABASE_URL` — Supabase **KisanRoute-Staging** PostgreSQL Transaction Pooler URI.
- `KISAN_ROUTE_SECRET_KEY` — unique long random session secret.
- `OWNER_PIN` and any required owner-only credentials — unique staging-only values.
- Existing integration credentials only when required for a staging test.

Never set the staging URI in Vercel Production scope. Never commit secrets or paste them into chat. The app also supports `KISAN_ROUTE_DATABASE_URL` and `SUPABASE_DB_URL`, but use one canonical variable (`DATABASE_URL`) per environment.

## 2. Backup before schema operations

Use the Supabase provider backup/snapshot facility where available, or:

```bash
pg_dump --format=custom --no-owner --file=kisanroute-staging-pre-guardian.dump "$DATABASE_URL"
pg_restore --list kisanroute-staging-pre-guardian.dump
```

Store the dump in encrypted private backup storage, not Git. Record timestamp and checksum. A backup is not verified until restored into a separate disposable database and the restored app can read expected records.

## 3. Apply additive Guardian schema

Review `migrations/sql/001_guardian_postgresql.sql`, then apply only to the staging database:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/sql/001_guardian_postgresql.sql
```

The SQL is additive and creates Guardian tables/indexes. SQLAlchemy models use the corresponding table names. The app currently calls `db.create_all()` at startup to create missing tables; it does not alter existing business tables. Prefer the explicit versioned migration and verify table/index presence before starting the worker.

## 4. Verify staging

Run:

```bash
python -m compileall -q .
python -m unittest discover -s tests -v
GUARDIAN_WORKER_ID=staging-smoke python guardian_daemon.py --once
```

The unit tests validate storage behavior against SQLite in-memory, not Supabase PostgreSQL. The one-cycle worker command must run only after staging `DATABASE_URL` is configured. Verify rows in `guardian_worker_heartbeats`, `guardian_logs`, `guardian_state`, `guardian_issues`, and `guardian_patches`. Confirm the project ref belongs to KisanRoute-Staging.

## 5. Continuous worker

Deploy `python guardian_daemon.py --interval 120` as a separate persistent background worker. Configure the same staging database and staging secrets. Do not run a persistent daemon inside Vercel serverless functions. Configure restart-on-failure and health alerts. Prevent duplicate cycles with a database-backed distributed lock before running more than one worker or enabling an overlapping cron pulse.

## 6. Rollback

1. Stop the staging worker.
2. Put the staging web app into maintenance mode.
3. Restore the pre-change snapshot into a fresh database (prefer a new database rather than destructive in-place restore).
4. Point staging `DATABASE_URL` to the restored database and redeploy the previous known-good staging revision.
5. Verify login, user records, bids, and Guardian dashboard.
6. Keep the failed database snapshot for investigation.

Do not drop Guardian tables as a rollback shortcut; preserve evidence and data. No production migration, deployment, or merge is authorized by this runbook.
