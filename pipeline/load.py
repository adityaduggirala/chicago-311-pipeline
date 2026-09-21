"""Load: idempotent upsert of raw records into DuckDB."""
from __future__ import annotations

import duckdb
import pandas as pd

from . import config

RAW_DDL = """
CREATE TABLE IF NOT EXISTS raw_requests (
    sr_number VARCHAR, sr_type VARCHAR, sr_short_code VARCHAR, owner_department VARCHAR,
    status VARCHAR, origin VARCHAR, created_date VARCHAR, last_modified_date VARCHAR,
    closed_date VARCHAR, zip_code VARCHAR, community_area VARCHAR, ward VARCHAR,
    latitude VARCHAR, longitude VARCHAR,
    _loaded_at TIMESTAMP DEFAULT current_timestamp
);
"""


def connect(path=None) -> duckdb.DuckDBPyConnection:
    path = path or config.DB_PATH
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(RAW_DDL)
    return con


def get_watermark(con) -> str | None:
    """Latest last_modified_date already loaded (drives incremental extraction)."""
    return con.execute("SELECT max(last_modified_date) FROM raw_requests").fetchone()[0]


def upsert_raw(con, df: pd.DataFrame) -> int:
    """Insert new versions of tickets. Tickets are versioned by (sr_number, last_modified_date)
    so re-running the same batch is a no-op (idempotent)."""
    if df.empty:
        return 0
    df = df.astype("string")
    con.register("incoming", df)
    before = con.execute("SELECT count(*) FROM raw_requests").fetchone()[0]
    con.execute("""
        INSERT INTO raw_requests (sr_number, sr_type, sr_short_code, owner_department, status,
            origin, created_date, last_modified_date, closed_date, zip_code, community_area,
            ward, latitude, longitude)
        SELECT i.sr_number, i.sr_type, i.sr_short_code, i.owner_department, i.status, i.origin,
               i.created_date, i.last_modified_date, i.closed_date, i.zip_code, i.community_area,
               i.ward, i.latitude, i.longitude
        FROM incoming i
        WHERE NOT EXISTS (
            SELECT 1 FROM raw_requests r
            WHERE r.sr_number = i.sr_number
              AND r.last_modified_date IS NOT DISTINCT FROM i.last_modified_date
        )
    """)
    con.unregister("incoming")
    return con.execute("SELECT count(*) FROM raw_requests").fetchone()[0] - before
