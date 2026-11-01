# Guardian worker deployment — staging only

## Verified repository state

- The Flask web application is deployed as a Vercel Python function via `vercel.json`.
- `guardian_daemon.py` is a separate persistent process; Vercel's function configuration does not launch it.
- Guardian state, logs, issues, patches and worker heartbeats are implemented using SQLAlchemy tables in `services/guardian/storage.py`.
- The PostgreSQL schema is also documented in `migrations/sql/001_guardian_postgresql.sql`.
- The app accepts `SUPABASE_DB_URL`, `KISAN_ROUTE_DATABASE_URL`, or `DATABASE_URL`; on Vercel it refuses to start without a persistent PostgreSQL URI and an explicit session secret.
- Unit tests exercise the Guardian SQL storage using SQLite in-memory. This is not a substitute for a real Supabase PostgreSQL staging test.
- No Supabase connection, schema migration, backup/restore test, or persistent worker deployment has been verified yet.

## Staging architecture

1. Keep the existing production Supabase project and live Vercel deployment unchanged.
2. Use the separate `KisanRoute-Staging` Supabase project for staging only.
3. Configure the Vercel Preview environment (or a separately named staging Vercel project) with that staging project's PostgreSQL Transaction Pooler URI as `DATABASE_URL` (or `KISAN_ROUTE_DATABASE_URL`). Never put the staging URI in Production environment scope.
4. Configure a unique `KISAN_ROUTE_SECRET_KEY` and owner-only Guardian secrets in the staging secret manager. Do not reuse production secrets.
5. Apply the additive Guardian SQL migration to the staging database after reviewing it. Take a provider snapshot or `pg_dump` first.
6. Deploy the web app from `market-readiness/hardening-phase-1` as a preview/staging deployment. Verify that the deployment is using the staging project ref, not the production project ref.
7. Provision a separate persistent background worker from the same branch and point it to the same staging PostgreSQL database. Start command: `python guardian_daemon.py --interval 120`.
8. Configure worker restart-on-failure and a unique `GUARDIAN_WORKER_ID`.
9. Verify fresh heartbeat records in `guardian_worker_heartbeats`, plus logs/state/issues/patches, before considering the worker active.

## Important compatibility checks

- Supabase Transaction Pooler is appropriate for short-lived serverless web requests; it uses IPv6 by default. Do not buy the IPv4 add-on unless the actual hosting network requires it.
- The dedicated long-running worker can use a direct or session-pooled connection depending on its network and connection lifetime. Do not blindly reuse the web app's transaction-pooler settings for the worker.
- Verify SQLAlchemy/psycopg2 compatibility with the chosen pooler and confirm the connection URI has the correct password URL-encoding. Never put a URI or password in Git, chat, screenshots, or logs.
- Do not enable both a cron pulse and a persistent worker for the same cycle until a database-backed distributed lock prevents duplicate runs.

## Verification checklist

- Confirm staging app's environment scope and Supabase project ref.
- Confirm database connectivity from the staging web deployment.
- Apply migration successfully and verify table/index presence.
- Run `python -m compileall -q .` and `python -m unittest discover -s tests -v`.
- Run one staging-only cycle: `GUARDIAN_WORKER_ID=staging-smoke python guardian_daemon.py --once`.
- Confirm heartbeat freshness, worker restart behavior, DB outage handling, owner-only access, and no cross-environment writes.
- Create a backup and restore it into a disposable database; verify expected tables and records.
- Check staging app workflows: login, farmer, wholesaler, bids, customer/order, driver, and Guardian dashboard.

## Not authorized / not yet done

- No production database changes, production environment variable edits, deployment, or merge.
- No staging credentials are committed.
- No claim of 24x7 monitoring until an external worker is deployed and fresh heartbeats are observed.
- No claim of staging readiness until real PostgreSQL migration, backup/restore, and end-to-end tests pass.
