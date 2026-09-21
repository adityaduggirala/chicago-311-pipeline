# Chicago 311 Data Pipeline

An incremental ELT pipeline and analytics dashboard for the City of Chicago's public
[311 Service Requests](https://data.cityofchicago.org/Service-Requests/311-City-Service-Requests/v6vf-nfxy)
dataset. It pulls data from the Socrata API, loads it idempotently into DuckDB, models it into a
star schema with SQL, gates it with data-quality checks, and serves it through a Streamlit dashboard.

```
Socrata API ──► extract (paged, watermark) ──► raw_requests (DuckDB)
                                                    │  idempotent upsert
                                                    ▼
                         sql/01_stg → 02_dim → 03_fct → 04_marts
                                                    │
                                 quality gates ─────┤ fail = pipeline stops
                                                    ▼
                                        Streamlit dashboard
```

## Highlights

- **Incremental extraction**: uses a `last_modified_date` watermark, so reruns only fetch new or changed tickets.
- **Idempotent loads**: re-running a batch inserts zero duplicate rows (tested).
- **Dedup by latest version**: tickets change status over time; staging keeps the newest version with a window function.
- **Dimensional model**: `stg_requests` → `dim_request_type` → `fct_requests` → four marts (daily volume, SLA percentiles, ward backlog, 7-day rolling average).
- **Data-quality gates**: null keys, uniqueness, temporal sanity, accepted values, geo bounds. A failure raises and stops the run.
- **Tested and CI'd**: pytest suite and GitHub Actions run the full pipeline on synthetic data.

## Quickstart

```bash
pip install -r requirements.txt
make run          # offline, generates 20k synthetic tickets
make test
make dashboard    # http://localhost:8501
```

Live data:

```bash
export SOCRATA_APP_TOKEN=...   # optional, free, raises rate limits
make run-api                   # incremental; run it again to see only new rows load
```

Or with Docker: `make docker`.

## Project layout

| Path | Purpose |
|---|---|
| `pipeline/extract.py` | Paged API client and synthetic sample generator |
| `pipeline/load.py` | DuckDB connection, watermark, idempotent upsert |
| `pipeline/transform.py` | Runs numbered `sql/*.sql` models in order |
| `pipeline/quality.py` | Data-quality checks |
| `sql/` | Staging, dimension, fact and mart models |
| `dashboard/app.py` | Streamlit dashboard |
| `tests/` | Unit and integration tests |

## Design decisions

- **DuckDB over Postgres**: zero-setup, columnar and fast for analytics; the SQL is portable to Postgres or BigQuery.
- **Raw layer stays all-`VARCHAR`**: type errors surface in staging (`TRY_CAST`) rather than breaking ingestion.
- **Versioned raw rows** keyed by `(sr_number, last_modified_date)` keep history and make loads replayable.

## Ideas to extend

- Orchestrate with Airflow or Prefect; port the SQL models to dbt.
- Add a geospatial ward heatmap (pydeck) and a forecast of daily volume.
- Write partitioned Parquet to S3 and query it through Athena.
