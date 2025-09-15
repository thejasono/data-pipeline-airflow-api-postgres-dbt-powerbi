# API → Postgres → dbt → Power BI

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

Power BI should connect using the `bi_read` credentials and only see tables in the `public_analytics` schema.

