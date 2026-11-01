# Market-readiness hardening: staging checklist

This branch contains an initial security-hardening patch. It is not approved for production deployment.

## Required production configuration

- `KISAN_ROUTE_SECRET_KEY`: long, random, unique Flask session-signing secret. Rotate any previously exposed value.
- `OWNER_PIN`: unique high-entropy owner PIN (not a reused/demo PIN).
- `OWNER_TOKEN`: long random token for the private owner automation endpoint; store only in a secret manager and send in an Authorization Bearer header.
- `ADMIN_PIN` and `GUARDIAN_ADMIN_TOKEN`: configure only if the legacy `/admin/guardian` interface is still required; use distinct secrets.
- `DATABASE_URL` (or `KISAN_ROUTE_DATABASE_URL` / `SUPABASE_DB_URL`): persistent managed PostgreSQL connection string. Do not use `/tmp` or SQLite for production state.
- `ENABLE_DEMO_ACCOUNTS`: local development only; never enable in production.

Never commit real values. Do not paste secrets into issues, pull requests, logs, or chat.

## Before staging deployment

1. Take a verified database backup and test restoring it to a separate staging database.
2. Confirm all existing users, bids, uploads, and operational records are preserved.
3. Rotate any credentials that may have been exposed by previous hard-coded defaults.
4. Configure persistent PostgreSQL and a stable Flask secret before starting the production app.
5. Run the full test suite and add coverage for owner identity/role authorization, CSRF, brute-force throttling, database persistence, and Guardian worker heartbeat.
6. Verify that private Guardian logs and APIs cannot be accessed by ordinary farmer, customer, driver, wholesaler, or cluster accounts.
7. Verify that the Guardian worker is actually deployed as a persistent worker or scheduled external job. A dashboard label is not proof of a running worker.
8. Test rollback against a staging snapshot before any production migration.

## Known work still required

- CSRF protection on all state-changing forms and endpoints.
- Distributed/persistent rate limiting; the current in-memory limiter is not sufficient across serverless instances.
- Server-side owner user identity and role verification; secret-based automation and browser owner sessions need separate, explicit policies.
- Durable database-backed Guardian state, logs, issues, patches, heartbeat, and concurrency-safe updates.
- Real worker deployment and truthful UNKNOWN/NOT CONFIGURED health reporting when no heartbeat is observed.
- Accurate provider usage and billing data; never infer zero cost from an estimated token counter.
- Business workflow persistence and end-to-end tests for orders, payments (sandbox only), and multi-driver GPS telemetry.

## Safety

This branch is isolated from `main`. Do not merge or deploy until the owner has reviewed the diff, the staging checklist is complete, and automated plus manual tests pass. No production database migration or deployment is authorized by this document.
