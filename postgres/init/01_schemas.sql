-- =============================================================================
-- Schema layout for ELT pipeline (executed at cluster bootstrap by Postgres'
-- entrypoint when placed under /docker-entrypoint-initdb.d/ in the image/container).
-- Purpose of each schema:
--   raw             → immutable(ish) landings from source systems; minimal shaping only.
--   public_staging  → cleaned/validated/intermediate transforms ready for modeling.
--   public_analytics → star/snowflake marts, semantic views, and BI-serving tables.
-- Power BI (read-only) should query *public_analytics* only.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw;
-- raw: "landing zone" for source data as-ingested.
-- - Stores the closest faithful copy of upstream payloads after *light* typing.
-- - No business logic or heavy joins; append-only patterns preferred.
-- - Enables reproducibility and late re-processing (dbt models can always
--   be rebuilt from raw). Acts as your single source of truth snapshot.

CREATE SCHEMA IF NOT EXISTS public_staging;
-- public_staging: "refinery" zone for deterministic cleaning and standardization.
-- - Apply type coercions, denormalization, de-duplication, surrogate keys,
--   basic conforming of dimensions, and integrity checks.
-- - Tables here are transient/derivative; dbt models typically materialize as
--   views or ephemeral tables that feed public_analytics.

CREATE SCHEMA IF NOT EXISTS public_analytics;
-- public_analytics: "presentation" / semantic layer for consumers (BI, notebooks).
-- - Star/snowflake schemas (fact_* and dim_*), or curated wide tables.
-- - Column names and types are business-friendly and stable.
-- - Only this schema will be granted to the bi_read role for least-privilege.

-- =============================================================================
-- Raw landing tables (typed columns kept simple; upstream UUIDs where available)
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.customers (
  customer_id UUID PRIMARY KEY,             -- stable entity key from source
  company_name TEXT,
  country TEXT,
  industry TEXT,
  company_size TEXT,
  signup_date TIMESTAMPTZ,                  -- always store timestamps in UTC
  updated_at TIMESTAMPTZ,
  is_churned BOOLEAN
);

CREATE TABLE IF NOT EXISTS raw.payments (
  payment_id UUID PRIMARY KEY,
  customer_id UUID,                          -- FK to raw.customers.customer_id (not enforced here in raw)
  product TEXT,
  amount NUMERIC,                            -- raw amounts; currency in separate column
  currency TEXT,
  status TEXT,
  refunded_amount NUMERIC,
  fee NUMERIC,
  payment_method TEXT,
  country TEXT,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_raw_payments_created ON raw.payments(created_at);
-- Minimal indexing in raw to support typical ingestion/merge windows and replay.

CREATE TABLE IF NOT EXISTS raw.sessions (
  session_id UUID PRIMARY KEY,
  customer_id UUID,
  source TEXT,                               -- e.g., google, newsletter
  medium TEXT,                               -- e.g., cpc, email
  campaign TEXT,
  device TEXT,
  country TEXT,
  pageviews INT,
  session_duration_s INT,
  bounced INT,                               -- 0/1 flags preserved as ingested
  converted INT,
  session_start TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_raw_sessions_start ON raw.sessions(session_start);

-- Notes:
-- - Foreign keys are intentionally not enforced in raw to avoid ingestion failure
--   due to upstream quality issues; enforce referential integrity in public_staging.
-- - Downstream (dbt) models should:
--     * stage_* (public_staging): coerce types, dedupe, apply FK checks
--     * dim_*/fact_* in public_analytics: expose curated entities/measures for BI
