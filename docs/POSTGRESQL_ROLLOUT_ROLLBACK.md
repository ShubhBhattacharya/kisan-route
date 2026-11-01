# PostgreSQL rollout and rollback runbook

This runbook applies to the isolated market-readiness branch. Do not point staging at production.

## 1. Provision and configure

Create a managed PostgreSQL database for staging and set these environment variables in the staging secret manager:
- `DATABASE_URL` — PostgreSQL connection string (never commit it).
- `KISAN_ROUTE_SECRET_KEY` — long random session secret.
- `OWNER_PIN` — unique owner PIN.
- `OWNER_PHONE` — phone number of the dedicated owner account, once owner-account verification is implemented.
- Any existing provider/API credentials required by the app.

Install dependencies from `requirements.txt`, including the PostgreSQL driver.

## 2. Backup before any schema operation

Use the database provider's snapshot facility or:
```bash
pg_dump --format=custom --no-owner --file=kisanroute-pre-guardian.dump "$DATABASE_URL"
pg_restore --list kisanroute-pre-guardian.dump
```
Store the dump in encrypted private backup storage, not in Git. Record its timestamp and checksum. A backup is not verified until it has been restored into a separate disposable database and the restored app can read expected users and bids.

## 3. Apply additive Guardian schema

Review `migrations/sql/001_guardian_postgresql.sql`, then:
```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/sql/001_guardian_postgresql.sql
```
The SQL is additive and creates only Guardian tables/indexes. The app's SQLAlchemy models use matching table names. Do not run the worker until this migration succeeds and the backup restore test passes.

The web app currently calls `db.create_all()` for missing tables. It does not alter existing business tables; future business schema changes require explicit versioned migrations.

## 4. Verify before enabling worker

Run:
```bash
python -m compileall -q .
python -m unittest discover -s tests -v
```
Then run a staging-only one-cycle worker:
```bash
GUARDIAN_WORKER_ID=staging-smoke python guardian_daemon.py --once
```
Check `guardian_worker_heartbeats`, `guardian_logs`, `guardian_state`, `guardian_issues` and `guardian_patches` in the staging database. Confirm no production credentials or production database are used.

## 5. Continuous worker

Deploy `python guardian_daemon.py --interval 120` as a separate always-on background worker service. Configure the same staging `DATABASE_URL` and secrets as the staging web app. Do not run a persistent daemon inside Vercel serverless functions. Configure restart-on-failure and provider health alerts.

## 6. Rollback

1. Stop the staging worker.
2. Put staging web app into maintenance mode.
3. Restore the pre-change snapshot into a fresh database (prefer a new database rather than destructive in-place restore).
4. Point staging `DATABASE_URL` to the restored database and redeploy the previous known-good application revision.
5. Verify login, user records, bids and Guardian dashboard.
6. Keep the failed database snapshot for investigation.

Do not drop Guardian tables as a rollback shortcut; preserve evidence and data. No production migration or deployment is authorized by this runbook.
