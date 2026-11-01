# Guardian AI Background Worker Deployment & Rollback Guide

This guide describes how to run `guardian_daemon.py` as a persistent 24×7 background worker on **Render** or **Railway**, completely separated from Vercel's ephemeral serverless frontend.

---

## 1. Architectural Overview

```
                      +---------------------------------------+
                      | Vercel Serverless (Frontend & API)    |
                      | Handles Web Traffic, Customer/Farmer  |
                      +-------------------+-------------------+
                                          |
                                          v
   +--------------------+     +-------------------------------+
   | Persistent Worker  |     | Managed PostgreSQL (Supabase) |
   | Render / Railway   | --> | Transaction Pooler (Port 6543)|
   | guardian_daemon.py |     | Six Guardian SQL Tables       |
   +--------------------+     +-------------------------------+
```

### Why a Separate Worker is Mandatory
- **Vercel Serverless Architecture:** Vercel functions are strictly event-driven HTTP request handlers. They enforce request timeouts (10 seconds by default on Hobby, 15–60 seconds on Pro, up to a hard maximum of 300 seconds). More crucially, serverless execution contexts freeze and terminate immediately after the HTTP response finishes, making long-running background loops (`while True` daemons) fundamentally unviable on Vercel.
- **Worker Role:** The dedicated worker runs `guardian_daemon.py --interval 120` as an isolated, persistent OS-level process. It performs periodic synthetic health checks, records heartbeats, and maintains state in the PostgreSQL database.

### Scope and Nature of Current Monitoring
> [!IMPORTANT]
> **Synthetic Workflow Verification Notice:**
> Guardian currently executes **synthetic workflow checks** (simulated end-to-end API and route inquiries against customer, farmer, cluster, driver, and wholesaler endpoints and PostgreSQL connectivity).
> It does **NOT** currently execute verified real-world AI monitoring or automated production code/schema remediation. Any issue logging or patch recommendation is an advisory synthetic proposal that requires explicit owner inspection and manual approval.

---

## 2. Option A: Render Deployment (Worker Service)

### A. Region Selection
Render hosts infrastructure in several primary regions: `singapore` (Southeast Asia), `frankfurt` (Europe Central), `oregon` (US West), `ohio` (US East), and `virginia` (US East).
For Supabase staging and production instances hosted in **AWS Mumbai (`ap-south-1`)**, Render's **`singapore`** region is the lowest-latency platform option (~30–50ms roundtrip latency compared to ~180–250ms for US/European regions).

### B. Setup Steps
1. In the Render Dashboard, click **New +** > **Background Worker**.
2. Connect your GitHub repository `ShubhBhattacharya/kisan-route`.
3. Select branch: `market-readiness/hardening-phase-1` (or your staging branch).
4. Render will auto-detect [`render.yaml`](../render.yaml) or configure manually:
   - **Environment:** `Python 3` (minor version `3.12` pinned in [`.python-version`](../.python-version))
   - **Region:** `Singapore` (`singapore`)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python guardian_daemon.py --interval 120`
5. Configure Environment Variables in Render:
   - `DATABASE_URL`: Staging Supabase PostgreSQL URI (`postgresql://postgres:[PASSWORD]@[HOST]:6543/postgres`).
   - `KISAN_ROUTE_SECRET_KEY`: Staging application session secret.
   - `GUARDIAN_WORKER_ID`: `render-worker-staging-01`
   - `PYTHONUNBUFFERED`: `1`

*(Note: `OWNER_PIN` and `OWNER_TOKEN` are browser authentication secrets for the web dashboard and are strictly excluded from the worker environment.)*

### C. Health & Restart Policy
- Render automatically restarts background workers upon uncaught exceptions.
- The worker records heartbeats every 120 seconds in the `guardian_worker_heartbeats` table.

---

## 3. Option B: Railway Deployment

### A. Setup Steps
1. In the Railway Dashboard, select **New Service** > **GitHub Repo**.
2. Railway detects [`railway.json`](../railway.json) and [`Procfile`](../Procfile).
3. Set the start command to:
   ```bash
   python guardian_daemon.py --interval 120
   ```
4. Set `restartPolicyType: ON_FAILURE` with max 10 retries.
5. Provide staging environment variables (`DATABASE_URL`, `KISAN_ROUTE_SECRET_KEY`, `GUARDIAN_WORKER_ID`, `PYTHONUNBUFFERED`) in the Railway Variables tab.

---

## 4. Platform & Deployment Troubleshooting

### Vercel Deployment Configurations
If builds fail on Vercel preview environments, check the following resolutions:

1. **`Python 3.12.x interpreter unavailable` (`kisan-route`, `kisan-route-8gv6`):**
   - **Cause:** Vercel's Python runtime (`@vercel/python`) requires minor-version specifications like `3.12`. Exact micro/patch pins (e.g. `3.12.10`) fail because Vercel looks for a minor-version release.
   - **Fix:** Pinned `3.12` in [`.python-version`](../.python-version) and updated CI workflows to match.
2. **`Root Directory 'kisan_route 2' does not exist` (`kisan-route-vrjb`):**
   - **Cause:** External configuration mismatch in Vercel Project Settings. The local folder on the developer machine was `kisan_route 2`, which was mistakenly entered into Vercel's Dashboard as the project Root Directory. In the Git repository, the files reside directly at repository root `.`.
   - **Action Required in Vercel Dashboard:**
     - Open project `kisan-route-vrjb` in Vercel Dashboard.
     - Go to **Settings** > **General** > **Root Directory**.
     - Clear `kisan_route 2` and reset to `./` (empty / repository root).
     - Save and trigger a new deployment.

---

## 5. Row Level Security (RLS) & Access Control Notes

When configuring PostgreSQL security policies:
1. **GRANT Privileges vs. RLS Policies:**
   - `REVOKE ALL ON ... FROM anon, authenticated` removes table-level privileges, blocking PostgREST queries immediately before RLS is evaluated.
   - RLS (`ENABLE ROW LEVEL SECURITY`) acts as row-level filtering for roles with table access.
2. **Supabase `service_role` Mechanics:**
   - In Supabase, `service_role` and `postgres` have the PostgreSQL `BYPASSRLS` attribute enabled by default. They automatically bypass RLS policies.
   - Explicit policies in [`migrations/sql/002_propose_guardian_rls_design.sql`](../migrations/sql/002_propose_guardian_rls_design.sql) provide defense-in-depth and serve as a specification, not a prerequisite for backend worker operations.
   - **Notice:** Keep RLS SQL scripts as proposals only until explicitly scheduled for migration.

---

## 6. Verification & Health Monitoring

After starting the worker, verify its live operation:

1. **Worker Console Log Output:**
   ```
   [Guardian] worker render-worker-staging-01 started successfully.
   [Guardian] cycle=healthy worker=render-worker-staging-01
   ```
2. **Database Verification (Read-Only):**
   ```sql
   SELECT worker_id, status, last_seen_at, last_cycle_at
   FROM guardian_worker_heartbeats;
   ```
   Confirm `status = 'running'` and `last_seen_at` is within the last 150 seconds.
3. **Owner Dashboard Check:**
   Open `/owner/guardian/` and verify that the Worker Status shows active and **Audit Cycles** increment automatically over time.

---

## 7. Failure Handling & Rollback Runbook

### Automatic Error Handling & Session Recovery
- If database connectivity drops or a cycle throws an error, the worker immediately calls `db.session.rollback()` to prevent transaction poisoning.
- It attempts to record a `degraded` heartbeat with the error type.
- If the database is completely unreachable, errors are printed to stdout/stderr without masking the underlying failure.
- Graceful shutdown (`SIGTERM` / `SIGINT`) rolls back any active transaction and attempts to record `stopped` status before terminating cleanly.

### Rollback Runbook
If the worker behaves unexpectedly or causes load spikes:
1. **Immediate Pause via Dashboard:**
   Open `/owner/guardian/` and click `[Pause Agent]`. The worker will detect `state.status == 'paused'` and sleep without executing cycles.
2. **Graceful Worker Shutdown:**
   In Render or Railway, click **Suspend Service** or **Stop Worker**.
   The process catches `SIGTERM` / `SIGINT` and updates `guardian_worker_heartbeats.status = 'stopped'`.
3. **Restore Last Known Good State:**
   - Stop the worker container.
   - Inspect `guardian_logs` for error traces:
     ```sql
     SELECT timestamp, level, event_type, message
     FROM guardian_logs
     ORDER BY created_at DESC LIMIT 10;
     ```
   - Redeploy the previous verified commit SHA.
