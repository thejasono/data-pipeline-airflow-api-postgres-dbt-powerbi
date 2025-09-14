-- =============================================================================
-- BI read-only user provisioning
-- Goal: allow Power BI (or other BI tools) to connect *only* to analytics schema
--       with SELECT privileges, and deny access to raw/staging.
-- Idempotent and safe to re-run.
-- =============================================================================

-- 1) Create or reset the login role (rotate password if it already exists)
DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bi_read') THEN
        CREATE ROLE bi_read LOGIN PASSWORD 'bi_read_password';
    ELSE
        ALTER ROLE bi_read WITH LOGIN PASSWORD 'bi_read_password';
    END IF;
END
$$;

-- 2) Base connectivity to the database
GRANT CONNECT ON DATABASE db TO bi_read;

-- 2a) Lock down non-analytics areas (defense-in-depth)
REVOKE USAGE ON SCHEMA raw FROM bi_read;
REVOKE USAGE ON SCHEMA staging FROM bi_read;
REVOKE SELECT ON ALL TABLES IN SCHEMA raw FROM bi_read;
REVOKE SELECT ON ALL TABLES IN SCHEMA staging FROM bi_read;
REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA raw FROM bi_read;
REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA staging FROM bi_read;

-- 2b) Grant least-privilege access to analytics only
GRANT USAGE ON SCHEMA analytics TO bi_read;                  -- can resolve names in the schema
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO bi_read;   -- can read current tables
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO bi_read;

-- 3) Future-proofing: default privileges for objects created later
--    These statements must be executed by the owner role that will create objects
--    (e.g., the role running dbt). They set *future* defaults, so new tables/
--    sequences in analytics are automatically readable by bi_read.
ALTER DEFAULT PRIVILEGES IN SCHEMA raw REVOKE ALL ON TABLES FROM bi_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw REVOKE ALL ON SEQUENCES FROM bi_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging REVOKE ALL ON TABLES FROM bi_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging REVOKE ALL ON SEQUENCES FROM bi_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO bi_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT USAGE, SELECT ON SEQUENCES TO bi_read;

-- 4) QoL: set search_path so unqualified names resolve to analytics first
ALTER ROLE bi_read SET search_path TO analytics, public;

-- Operational notes:
-- - Rotate 'bi_read_password' via env/secret management; don't hardcode in prod.
-- - Ensure your modeling tool (e.g., dbt) runs with a role that *owns* analytics
--   objects; otherwise alter default privileges must be run by that owning role.
-- - Power BI connection string: point to database `db`, user `bi_read`, and set
--   SSL params as required by your deployment.
