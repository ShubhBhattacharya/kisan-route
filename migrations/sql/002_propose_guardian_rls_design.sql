-- ==============================================================================
-- PROPOSED ROW LEVEL SECURITY (RLS) POLICIES FOR KISANROUTE GUARDIAN AI TABLES
-- ==============================================================================
-- STATUS: PROPOSED / SPECIFICATION ONLY. DO NOT APPLY DIRECTLY WITHOUT OWNER APPROVAL.
-- CONTEXT:
--   The KisanRoute Guardian AI uses six relational tables in PostgreSQL:
--     1. guardian_state
--     2. guardian_logs
--     3. guardian_issues
--     4. guardian_patches
--     5. guardian_worker_heartbeats
--     6. guardian_import_ledger
--
-- RATIONALE & ACCESS MATRIX:
--   - Web Application & Background Worker connect using backend credentials (e.g. postgres / service_role).
--   - Public anonymous users ('anon') and standard logged-in users ('authenticated' e.g. farmers,
--     customers, drivers, wholesalers) must NEVER read, write, or enumerate Guardian AI telemetry.
--   - If Supabase PostgREST or Data API is enabled on the project, blind RLS without policies
--     locks everything out, but default permissive RLS risks exposing system logs to the anon key.
--   - Therefore, the safest design:
--       1) Enable RLS on all six Guardian tables.
--       2) Grant FULL access exclusively to 'service_role' (the trusted backend identity).
--       3) Revoke all privileges from 'anon' and 'authenticated'.
-- ==============================================================================

-- 1. Enable RLS on all six Guardian tables
ALTER TABLE IF EXISTS guardian_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS guardian_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS guardian_issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS guardian_patches ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS guardian_worker_heartbeats ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS guardian_import_ledger ENABLE ROW LEVEL SECURITY;

-- 2. Revoke permissions from untrusted public / client roles
REVOKE ALL ON TABLE guardian_state FROM anon, authenticated;
REVOKE ALL ON TABLE guardian_logs FROM anon, authenticated;
REVOKE ALL ON TABLE guardian_issues FROM anon, authenticated;
REVOKE ALL ON TABLE guardian_patches FROM anon, authenticated;
REVOKE ALL ON TABLE guardian_worker_heartbeats FROM anon, authenticated;
REVOKE ALL ON TABLE guardian_import_ledger FROM anon, authenticated;

-- 3. Explicit Service Role Policy (Permit trusted backend service operations)
-- Table: guardian_state
DROP POLICY IF EXISTS guardian_state_service_role_policy ON guardian_state;
CREATE POLICY guardian_state_service_role_policy
    ON guardian_state
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Table: guardian_logs
DROP POLICY IF EXISTS guardian_logs_service_role_policy ON guardian_logs;
CREATE POLICY guardian_logs_service_role_policy
    ON guardian_logs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Table: guardian_issues
DROP POLICY IF EXISTS guardian_issues_service_role_policy ON guardian_issues;
CREATE POLICY guardian_issues_service_role_policy
    ON guardian_issues
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Table: guardian_patches
DROP POLICY IF EXISTS guardian_patches_service_role_policy ON guardian_patches;
CREATE POLICY guardian_patches_service_role_policy
    ON guardian_patches
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Table: guardian_worker_heartbeats
DROP POLICY IF EXISTS guardian_worker_heartbeats_service_role_policy ON guardian_worker_heartbeats;
CREATE POLICY guardian_worker_heartbeats_service_role_policy
    ON guardian_worker_heartbeats
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Table: guardian_import_ledger
DROP POLICY IF EXISTS guardian_import_ledger_service_role_policy ON guardian_import_ledger;
CREATE POLICY guardian_import_ledger_service_role_policy
    ON guardian_import_ledger
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
