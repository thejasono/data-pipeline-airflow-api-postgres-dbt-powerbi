# API → Postgres → dbt → Power BI
![Diagramtic](https://github.com/user-attachments/assets/5e84b667-0f24-46bb-85e6-ee05d4039685)

This stack loads raw data from the mock API into Postgres, transforms it with dbt, and exposes cleaned analytics tables (materialized in the `public_analytics` schema) for the `bi_read` user.

## Services

- **postgres** – database used by all components
- **mock-api** – provides sample API data
- **dbt** – dbt CLI container with the project mounted at `/usr/app`
- **airflow** – orchestrates extraction and dbt transformations

## Usage

Start the core services (dbt is invoked on-demand by the Airflow DAG):

```bash
docker compose up -d postgres mock-api airflow
```

Airflow performs its own database initialization on startup, so no separate init container is required.

The DAG will execute dbt via `docker compose run --rm dbt ...` after extracting raw data.
You can still run dbt manually if needed:

```bash
docker compose run --rm dbt run
docker compose run --rm dbt test
```

Power BI usage for this project is intentionally lightweight—the goal is simply to prove the pipeline delivers
analytics tables that Power BI can read. Connect with the `bi_read` credentials and verify that the
`public_analytics` schema tables are visible. A fully designed report or synthetic visuals are not required for
sign-off.

