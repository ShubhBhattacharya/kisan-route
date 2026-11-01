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

- **Why separate?** Vercel serverless execution times out after 10–15 seconds and freezes background loops.
- **Worker role:** Runs `guardian_daemon.py --interval 120` in an infinite process loop, executing synthetic tests and heartbeats.

---

## 2. Option A: Render Deployment (Worker Service)

### A. Setup Steps
1. In Render Dashboard, click **New +** > **Background Worker**.
2. Connect GitHub repository `ShubhBhattacharya/kisan-route`.
3. Select branch: `market-readiness/hardening-phase-1` (or your staging branch).
4. Render will auto-detect [`render.yaml`](file:///c:/Users/prate/OneDrive/Desktop/kisan_route/kisan_route%202/render.yaml) or configure manually:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python guardian_daemon.py --interval 120`
5. Configure Environment Variables in Render:
   - `DATABASE_URL`: Staging Supabase PostgreSQL URI.
   - `KISAN_ROUTE_SECRET_KEY`: Staging session secret.
   - `OWNER_PIN`: Owner security PIN.
   - `OWNER_TOKEN`: Owner Bearer token.
   - `GUARDIAN_WORKER_ID`: `render-worker-staging-01`
   - `PYTHONUNBUFFERED`: `1`

### B. Health & Restart Policy
- Render automatically restarts background workers upon uncaught exceptions.
- The worker records heartbeats every 120s in the `guardian_worker_heartbeats` table.

---

## 3. Option B: Railway Deployment

### A. Setup Steps
1. In Railway Dashboard, select **New Service** > **GitHub Repo**.
2. Railway detects [`railway.json`](file:///c:/Users/prate/OneDrive/Desktop/kisan_route/kisan_route%202/railway.json) and [`Procfile`](file:///c:/Users/prate/OneDrive/Desktop/kisan_route/kisan_route%202/Procfile).
3. Set the start command to:
   ```bash
   python guardian_daemon.py --interval 120
   ```
4. Set `restartPolicyType: ON_FAILURE` with max 10 retries.
5. Provide staging environment variables in the Railway Variables tab.

---

## 4. Verification & Health Monitoring

After starting the worker, verify health:
1. **Worker Console Log Output:**
   ```
   [Guardian] cycle=healthy worker=render-worker-staging-01
   ```
2. **Database Verification (Read-Only):**
   ```sql
   SELECT worker_id, status, last_seen_at, last_cycle_at
   FROM guardian_worker_heartbeats;
   ```
   Confirm `status = 'running'` and `last_seen_at` is within the last 150 seconds.
3. **Owner Dashboard Check:**
   Open `/owner/guardian/` and verify that **Audit Cycles** increment automatically without clicking buttons.

---

## 5. Rollback Runbook

If the worker behaves unexpectedly or causes load spikes:
1. **Immediate Pause via Dashboard:**
   Open `/owner/guardian/` and click `[Pause Agent]`. The worker will detect `state.status == 'paused'` and sleep without executing cycles.
2. **Graceful Worker Shutdown:**
   In Render / Railway, click **Suspend Service** or **Stop Worker**.
   The process catches `SIGTERM` / `SIGINT` and updates `guardian_worker_heartbeats.status = 'stopped'`.
3. **Restore Last Known Good State:**
   - Stop the worker container.
   - Check `guardian_logs` for error traces:
     ```sql
     SELECT timestamp, level, event_type, message
     FROM guardian_logs
     ORDER BY created_at DESC LIMIT 10;
     ```
   - Redeploy the previous verified commit.
