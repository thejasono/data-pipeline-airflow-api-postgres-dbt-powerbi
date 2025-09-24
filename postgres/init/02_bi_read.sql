-- =============================================================================
-- BI read-only user provisioning
-- Goal: allow Power BI (or other BI tools) to read public_analytics and raw
--       with SELECT privileges; deny public and public_staging.
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

-- 2a) Deny access to public_staging and public (defense-in-depth)
REVOKE USAGE ON SCHEMA public_staging FROM bi_read;
REVOKE SELECT ON ALL TABLES    IN SCHEMA public_staging FROM bi_read;
REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public_staging FROM bi_read;

REVOKE USAGE ON SCHEMA public FROM bi_read;
REVOKE SELECT ON ALL TABLES    IN SCHEMA public FROM bi_read;
REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM bi_read;

-- 2b) Grant read-only on target schemas (current objects)

-- raw
GRANT USAGE ON SCHEMA raw TO bi_read;
GRANT SELECT ON ALL TABLES    IN SCHEMA raw TO bi_read;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA raw TO bi_read;

-- public_analytics
GRANT USAGE ON SCHEMA public_analytics TO bi_read;
GRANT SELECT ON ALL TABLES    IN SCHEMA public_analytics TO bi_read;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public_analytics TO bi_read;

-- 3) Future-proofing: default privileges for *new* objects
--    IMPORTANT: run these as the role that will CREATE objects in each schema
--    (e.g., your dbt/ingest role, not necessarily as bi_read).

-- public_staging: ensure future objects are NOT granted to bi_read
ALTER DEFAULT PRIVILEGES IN SCHEMA public_staging REVOKE ALL ON TABLES    FROM bi_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public_staging REVOKE ALL ON SEQUENCES FROM bi_read;

-- public: ensure future objects are NOT granted to bi_read
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES    FROM bi_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM bi_read;

-- raw
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO bi_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT USAGE, SELECT ON SEQUENCES TO bi_read;

-- public_analytics
ALTER DEFAULT PRIVILEGES IN SCHEMA public_analytics GRANT SELECT ON TABLES TO bi_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public_analytics GRANT USAGE, SELECT ON SEQUENCES TO bi_read;

-- 4) QoL: make name resolution predictable (analytics first, raw second)
ALTER ROLE bi_read SET search_path TO public_analytics, raw;

-- Operational notes:
-- - Rotate 'bi_read_password' via secret management.
-- - Ensure the role that creates objects in each schema runs the ALTER DEFAULT PRIVILEGES.
-- - If Row-Level Security (RLS) is enabled on any target tables, define SELECT policies for bi_read.
