-- ==============================================================================
-- PROPOSED ROW LEVEL SECURITY (RLS) POLICIES FOR KISANROUTE GUARDIAN AI TABLES
-- ==============================================================================
-- STATUS: PROPOSED / SPECIFICATION ONLY. DO NOT APPLY DIRECTLY TO DATABASE.
--
-- CONTEXT:
--   The KisanRoute Guardian AI uses six relational tables in PostgreSQL:
--     1. guardian_state
--     2. guardian_logs
--     3. guardian_issues
--     4. guardian_patches
--     5. guardian_worker_heartbeats
--     6. guardian_import_ledger
--
-- TECHNICAL AUDIT & ARCHITECTURAL DISTINCTIONS:
--   1. GRANT Privileges vs. Row Level Security (RLS) Policies:
--      - SQL GRANT / REVOKE manages table-level discretionary access control (DAC).
--        If a role has no SELECT/INSERT privilege on a table, PostgreSQL denies the
--        request immediately; RLS policies are never even reached or evaluated.
--      - RLS filters and restricts which individual rows an authorized role can read
--        or write (tuple-level access control).
--      - Enabling RLS (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`) without policies
--        causes PostgreSQL to default to DENY-ALL for all non-bypassing roles.
--
--   2. Supabase Role Mechanics & BYPASSRLS Verification:
--      - `postgres` (Superuser / Direct Connection / Pooler):
--        Possesses the PostgreSQL `BYPASSRLS` role attribute by default.
--        Direct SQLAlchemy connections from Render / Railway / Vercel using the
--        direct connection string bypass all RLS policies entirely.
--      - `service_role` (Trusted Backend Service Key via Supabase PostgREST):
--        In standard Supabase infrastructure, the `service_role` PostgreSQL role is
--        explicitly granted the `BYPASSRLS` attribute. Therefore, `service_role`
--        automatically bypasses RLS policies in PostgREST by platform design.
--        Creating explicit RLS policies for `service_role` serves purely as an
--        in-depth safeguard in custom environments where `BYPASSRLS` might be revoked.
--      - `anon` and `authenticated` (Untrusted Client Roles):
--        Used by public visitors and standard logged-in users (farmers, customers,
--        drivers, wholesalers) accessing PostgREST APIs.
--        In Supabase, schema `public` tables receive default grants to `anon` and
--        `authenticated`. Therefore, untrusted roles MUST have their privileges
--        revoked at the table level (`REVOKE ALL`) AND have zero permissive RLS policies.
--
-- RECOMMENDATION SUMMARY:
--   - Defense-in-depth: Revoke table-level access from `anon` and `authenticated`.
--   - Enable RLS on all six Guardian tables.
--   - Explicitly permit backend operations for `service_role` as an architectural specification.
--   - Keep this migration unapplied until approved by the repository owner.
-- ==============================================================================

-- 1. Enable RLS on all six Guardian tables
ALTER TABLE IF EXISTS guardian_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS guardian_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS guardian_issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS guardian_patches ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS guardian_worker_heartbeats ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS guardian_import_ledger ENABLE ROW LEVEL SECURITY;

-- 2. Revoke table-level privileges from public / client roles (Discretionary Access Control)
REVOKE ALL ON TABLE guardian_state FROM anon, authenticated;
REVOKE ALL ON TABLE guardian_logs FROM anon, authenticated;
REVOKE ALL ON TABLE guardian_issues FROM anon, authenticated;
REVOKE ALL ON TABLE guardian_patches FROM anon, authenticated;
REVOKE ALL ON TABLE guardian_worker_heartbeats FROM anon, authenticated;
REVOKE ALL ON TABLE guardian_import_ledger FROM anon, authenticated;

-- 3. Explicit Service Role Policies (Defense-in-depth for backend service operations)
-- Note: On standard Supabase, service_role possesses BYPASSRLS and already bypasses these filters.

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
