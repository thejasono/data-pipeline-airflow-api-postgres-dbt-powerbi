import os, time, requests, logging
from datetime import datetime, timedelta
from dateutil import parser
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
from airflow.operators.bash import BashOperator

API_BASE = os.environ.get("API_BASE_URL", "http://mock-api:8000")
API_KEY = os.environ["API_KEY"]
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

DEFAULT_ARGS = {
    "owner": "data",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

def _get_watermark(name, default_iso):
    return Variable.get(name, default_var=default_iso)

def _set_watermark(name, iso):
    Variable.set(name, iso)

def _fetch_paged(endpoint, params, max_retries=5):
    page = 1
    while True:
        p = params.copy()
        p.update({"page": page, "page_size": 500})
        r = None
        for attempt in range(max_retries):
            try:
                r = requests.get(
                    f"{API_BASE}/{endpoint}",
                    headers=HEADERS,
                    params=p,
                    timeout=30,
                )
            except requests.exceptions.RequestException as e:
                logging.warning("Request to %s failed (%s)", endpoint, e)
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 429:
                retry = r.json().get("retry_after", 10)
                time.sleep(int(retry))
                continue
            if r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            data = r.json()
            yield data
            break
        else:
            logging.error(
                "Failed to fetch %s with params %s after %s attempts (last status %s)",
                endpoint,
                p,
                max_retries,
                getattr(r, "status_code", "unknown"),
            )
            raise RuntimeError(
                f"Failed to fetch {endpoint} after {max_retries} attempts",
            )
        if data.get("next_page"):
            page = data["next_page"]
        else:
            return

def extract_table(table, endpoint, ts_field, wm_name):
    pg = PostgresHook(postgres_conn_id="postgres_default")
    iso_default = (datetime.utcnow() - timedelta(days=365)).isoformat() + "Z"
    watermark = _get_watermark(wm_name, iso_default)
    max_seen = parser.isoparse(watermark)
    rows = 0
    for page in _fetch_paged(endpoint, {"updated_since": watermark}):
        data = page["data"]
        if not data:
            continue
        with pg.get_conn() as conn:
            with conn.cursor() as cur:
                if table == "raw.customers":
                    cur.executemany(
                        """
                        INSERT INTO raw.customers(customer_id,company_name,country,industry,company_size,signup_date,updated_at,is_churned)
                        VALUES(%(customer_id)s,%(company_name)s,%(country)s,%(industry)s,%(company_size)s,%(signup_date)s,%(updated_at)s,%(is_churned)s)
                        ON CONFLICT (customer_id) DO UPDATE SET
                          company_name=EXCLUDED.company_name,
                          country=EXCLUDED.country,
                          industry=EXCLUDED.industry,
                          company_size=EXCLUDED.company_size,
                          signup_date=EXCLUDED.signup_date,
                          updated_at=EXCLUDED.updated_at,
                          is_churned=EXCLUDED.is_churned
                        """,
                        data
                    )
                elif table == "raw.payments":
                    cur.executemany(
                        """
                        INSERT INTO raw.payments(payment_id,customer_id,product,amount,currency,status,refunded_amount,fee,payment_method,country,created_at,updated_at)
                        VALUES(%(payment_id)s,%(customer_id)s,%(product)s,%(amount)s,%(currency)s,%(status)s,%(refunded_amount)s,%(fee)s,%(payment_method)s,%(country)s,%(created_at)s,%(updated_at)s)
                        ON CONFLICT (payment_id) DO UPDATE SET
                          customer_id=EXCLUDED.customer_id,
                          product=EXCLUDED.product,
                          amount=EXCLUDED.amount,
                          currency=EXCLUDED.currency,
                          status=EXCLUDED.status,
                          refunded_amount=EXCLUDED.refunded_amount,
                          fee=EXCLUDED.fee,
                          payment_method=EXCLUDED.payment_method,
                          country=EXCLUDED.country,
                          created_at=EXCLUDED.created_at,
                          updated_at=EXCLUDED.updated_at
                        """,
                        data
                    )
                else:
                    for d in data:
                        # API returns booleans; cast to ints for raw schema
                        d["bounced"] = int(d.get("bounced", False))
                        d["converted"] = int(d.get("converted", False))
                    cur.executemany(
                        """
                        INSERT INTO raw.sessions(session_id,customer_id,source,medium,campaign,device,country,pageviews,session_duration_s,bounced,converted,session_start,updated_at)
                        VALUES(%(session_id)s,%(customer_id)s,%(source)s,%(medium)s,%(campaign)s,%(device)s,%(country)s,%(pageviews)s,%(session_duration_s)s,%(bounced)s,%(converted)s,%(session_start)s,%(updated_at)s)
                        ON CONFLICT (session_id) DO NOTHING
                        """,
                        data
                    )
        rows += len(data)
        for d in data:
            ts = parser.isoparse(d.get(ts_field))
            if ts > max_seen:
                max_seen = ts
    _set_watermark(wm_name, max_seen.isoformat())
    return rows

with DAG(
    dag_id="etl_api_to_bi",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule_interval="*/15 * * * *",
    catchup=False,
    tags=["api", "postgres", "dbt", "bi"],
) as dag:

    extract_customers = PythonOperator(
        task_id="extract_customers",
        python_callable=extract_table,
        op_kwargs={
            "table": "raw.customers",
            "endpoint": "customers",
            "ts_field": "updated_at",
            "wm_name": "wm_customers",
        },
    )

    extract_payments = PythonOperator(
        task_id="extract_payments",
        python_callable=extract_table,
        op_kwargs={
            "table": "raw.payments",
            "endpoint": "payments",
            "ts_field": "updated_at",
            "wm_name": "wm_payments",
        },
    )

    extract_sessions = PythonOperator(
        task_id="extract_sessions",
        python_callable=extract_table,
        op_kwargs={
            "table": "raw.sessions",
            "endpoint": "sessions",
            "ts_field": "updated_at",
            "wm_name": "wm_sessions",
        },
    )

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=(
            "docker exec dbt bash -lc "
            "'cd /usr/app && dbt deps --profiles-dir /root/.dbt'"
        ),
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            "docker exec dbt bash -lc "
            "'cd /usr/app && dbt build --fail-fast --profiles-dir /root/.dbt'"
        ),
    )


    [extract_customers, extract_payments, extract_sessions] >> dbt_deps >> dbt_build
