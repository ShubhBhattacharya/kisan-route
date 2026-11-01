# Guardian worker deployment — staging only

## Current truth
The repository contains `guardian_daemon.py`, but Vercel's serverless function configuration does not deploy it as a persistent process. The JSON storage module currently writes beneath `/tmp/guardian_data` on Vercel, which is ephemeral and not shared reliably between function instances. Therefore the current deployment must not be represented as 24x7 monitored.

The dashboard now starts from an unconfigured/unknown state and avoids claiming 100% uptime or a zero-dollar AI bill without usage evidence.

## Recommended staging architecture
1. Keep the Flask web app on Vercel.
2. Provision a separate always-on worker service (for example, a Render Background Worker or equivalent container worker) from the same Git repository.
3. Worker start command: `python guardian_daemon.py --interval 120`.
4. Configure the worker and web service to use the same managed PostgreSQL database.
5. Replace the JSON-file Guardian state/log/issue/patch store with transactional PostgreSQL tables before enabling the worker. Do not mount a shared writable local filesystem or rely on `/tmp`.
6. Add a worker heartbeat table with worker ID, last_seen_at, process status, and last successful cycle. Dashboard health should be active only when the heartbeat is fresh (for example, under 5 minutes); otherwise show stale/offline/unknown.
7. Use a distributed lock or database advisory lock so two workers cannot run the same cycle concurrently.
8. Store AI provider, model, request ID, input/output token counts, estimated/actual cost, timestamp and outcome for each real provider call. Unknown costs must remain unknown.
9. Configure secret values in the provider's secret manager only; never commit them.
10. Test worker restart, database outage, duplicate-cycle prevention, stale-heartbeat display, and restore from backup in staging.

## Do not enable yet
Do not start a production worker until the Guardian storage migration, DB backup/restore, owner-only authorization tests, and staging verification have passed. Do not point a staging worker at the production database.
