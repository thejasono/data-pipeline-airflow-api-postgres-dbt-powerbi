# postgres_init_summary.py
"""
Purpose
-------
This file explains what the Postgres init SQL files do, when they run in container lifecycle,
and how they fit into the Airflow → dbt → Power BI pipeline.

Files Covered
-------------
1) init/01_schemas.sql
   - Creates logical schemas: raw, public_staging, public_analytics
   - Creates landing tables in raw (customers, payments, sessions)
2) init/02_bi_read.sql
   - Provisions a read-only login/role `bi_read`
   - Restricts access to only the `public_analytics` schema (least-privilege)
   - Sets default privileges so future public_analytics objects are readable

When These Scripts Execute
--------------------------
• These run automatically during *Postgres container initialization* when using the
  official postgres image (or compatible). Any *.sql, *.sql.gz, *.sh* under:
      /docker-entrypoint-initdb.d/
  are executed **only on first boot** when the data directory (PGDATA) is empty.
  After the database has been initialized, these files will NOT run again.

• In docker-compose:
    - If you mount a host folder `./postgres/init` to the container path
      `/docker-entrypoint-initdb.d/`, the entrypoint will pick them up on first run.
    - If you remove the volume (or wipe PGDATA) and recreate the container,
      the scripts will run again (fresh cluster).

Execution Order
---------------
• Filenames are processed in lexicographical order (I don't know what this means) by the entrypoint.
  → `01_schemas.sql` runs before `02_bi_read.sql` (desired).
• Keep idempotency: use IF NOT EXISTS / REVOKE/GRANT patterns so re-runs are safe.
(what does idemopotency even mean?)

Role of Each Schema (High-Level)
--------------------------------
• raw:
    - Landing zone. Light typing, minimal constraints. Source-of-truth snapshots.
• public_staging (dbt "staging" layer):
    - Cleaning zone. Type coercion, dedupe, referential integrity checks, surrogates.
    - Populated by dbt **staging SQL models** in `dbt/models/staging`. When you run dbt,
      those .sql files are compiled into views such as `public_staging.stg_customers`,
      `public_staging.stg_payments`, and `public_staging.stg_sessions`.
    - You do **not** need to create these views manually in the Postgres init scripts;
      dbt materializes them. Before dbt runs, only the raw tables (`raw.customers`,
      `raw.payments`, `raw.sessions`) exist. After dbt runs, the staging views appear in
      addition to the raw tables.
• public_analytics (dbt "analytics" layer):
    - Presentation/semantic layer for BI. Star/snowflake marts, curated views/tables.

dbt Staging Models: Practical Notes
-----------------------------------
• Purpose of staging SQL files: Centralize cleansing/standardization logic so dbt can
  maintain the staging layer for you.
• You might not immediately see the `public_staging` schema in a fresh database because
  its objects are created only once dbt has run. Leave the schema definition in
  `01_schemas.sql`—it is required for dbt to materialize its views, even if it looks
  empty at first.
• If you *really* wanted to create placeholder tables via SQL (e.g., in `01_schemas.sql`),
  you could, but it is unnecessary. dbt will manage the staging views once executed.

Access Snapshot
---------------
• Before running dbt: Raw tables only.
• After running dbt: Raw tables **plus** the staging views defined in
  `dbt/models/staging`.

Airflow/dbt/Power BI Flow (Where These Fit)
-------------------------------------------
1) Airflow orchestrates:
   - Extract tasks load data into `raw` (via COPY/INSERT or external loaders).
   (How exactly I have this function, does it do it for me):
   - Transform tasks (dbt or SQL operators) read from `raw`, produce "staging" models
     (materialized in `public_staging`), then produce "analytics" models (dim_*,
     fact_*, views) materialized in `public_analytics`.
2) dbt (typical):
   - Models: stage_* (`public_staging`) → dim_*/fact_* (`public_analytics`).
   - Owner/role running dbt should own objects in `public_analytics` so default privileges
     (grants to `bi_read`) apply automatically.
3) Power BI:
   - Connects with user `bi_read` (read-only).
   - Has CONNECT on database `db` + USAGE on `public_analytics` + SELECT on public_analytics tables.

Security/Permissions Model
--------------------------
• `bi_read`:
    - Can connect to DB.
    - Cannot use or read `raw` / `public_staging`.
    - Can use `public_analytics`, read existing tables/sequences.
    - Via ALTER DEFAULT PRIVILEGES, also gains read access to *future* public_analytics tables.
• Run ALTER DEFAULT PRIVILEGES as the same owning role that will create public_analytics objects.
  If run by a different role, defaults won’t apply.

Local Dev vs Prod Considerations
--------------------------------
• Password management:
    - Replace hardcoded 'bi_read_password' with secret mgmt (env, Vault, Kubernetes Secret).
• Ownership:
    - Ensure the modeling/transform role (e.g., dbt runner) is the owner of public_analytics objects.
• Schema evolution:
    - Keep `01_schemas.sql` minimal. Use migrations/dbt for ongoing DDL changes, not the init hook.
• Reprovisioning:
    - Dropping the volume will re-run init scripts. Avoid in prod unless intentional.

How To Mount Init Scripts (compose example)
-------------------------------------------
# docker-compose.yml (excerpt)
# services:
#   postgres:
#     image: postgres:16
#     environment:
#       POSTGRES_DB: db
#       POSTGRES_USER: app
#       POSTGRES_PASSWORD: app_password
#     volumes:
#       - pgdata:/var/lib/postgresql/data
#       - ./postgres/init:/docker-entrypoint-initdb.d:ro
# volumes:
#   pgdata:

Validation Checklist (quick tests)
----------------------------------
• As admin role:
# \dn                 -- schemas exist?
# \dt raw.*           -- raw tables created?
• As bi_read:
# SELECT * FROM public_analytics.some_table; -- should succeed (after public_analytics exists)
# SELECT * FROM raw.customers;               -- should fail (no permission)
• Create a new public_analytics table as the owner and verify bi_read can read it without extra GRANT.

Common Pitfalls
---------------
• Running ALTER DEFAULT PRIVILEGES as the wrong role (defaults won’t apply).
• Expecting init scripts to run on every container start (they don’t; first init only).
• Enforcing strict FKs in raw causing ingestion failures—prefer to enforce in public_staging/public_analytics.
• Forgetting timezone consistency (TIMESTAMPTZ in UTC).

TODOs (fill in project-specific details)
----------------------------------------
# 1) Identify the role that runs dbt and confirm it owns public_analytics objects:
#    OWNER ROLE: ______________________________________
#
# 2) Confirm Power BI connection parameters:
#    HOST: __________  PORT: 5432  DB: db  USER: bi_read  SSLMODE: require/disable (pick one)
#
# 3) List critical public_analytics tables Power BI depends on:
#    - public_analytics.dim_customer
#    - public_analytics.fact_payment
#    - public_analytics.fact_session
#
# 4) Note any required indexes for BI performance (add in public_analytics, not raw):
#    - CREATE INDEX ... ON public_analytics.fact_payment (customer_id, created_at);
#
# 5) Document sensitive data handling (masking, row-level controls if needed):
#    - _____________________________________________
#
# 6) Decide migration path for schema changes post-initialization:
#    - Use dbt migrations / Alembic / manual DDL? ______________________________
"""

# (Optional) Tiny runtime helper to print an at-a-glance summary in logs
def print_pipeline_summary():
    print(
        "\nPostgres Init Summary\n"
        "---------------------\n"
        "Schemas:\n"
        "  raw             = landing zone (light typing, minimal constraints)\n"
        "  public_staging  = cleaning/refinery (coercions, dedupe, integrity)\n"
        "  public_analytics = BI presentation (star/snowflake, curated views)\n\n"
        "Init timing:\n"
        "  Runs once when PGDATA is empty via /docker-entrypoint-initdb.d/*\n\n"
        "Access:\n"
        "  bi_read    = read-only, public_analytics-only access for Power BI\n"
    )


if __name__ == "__main__":
    # For ad-hoc sanity checks (e.g., when this file is executed in a tools container)
    print_pipeline_summary()
