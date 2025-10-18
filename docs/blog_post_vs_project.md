# Blog Post vs. Project Differences

| Blog Post Claim | Actual Project Implementation | Correction Needed |
| --- | --- | --- |
| Watermarks are stored in a dedicated `watermarks` table created by the Postgres init scripts. | The pipeline reads and writes watermarks via Airflow Variables; the Postgres bootstrap scripts only create schemas and raw tables—no `watermarks` table exists. | Update the blog/script to explain that Airflow Variables hold the incremental load watermarks (or add the table to the repo if desired). |
| DAG imports the hook from `airflow.hooks.postgres_hook`. | The DAG uses the provider package import `airflow.providers.postgres.hooks.postgres.PostgresHook`. | Align the blog/script with the provider-style import so readers copy the working code. |
| The BI user only has access to the analytics schema. | `02_bi_read.sql` grants the `bi_read` role `USAGE/SELECT` on both `public_analytics` **and** `raw`. | Either adjust the blog/script to mention the raw schema access, or tighten the SQL to restrict the role to `public_analytics` only. |

