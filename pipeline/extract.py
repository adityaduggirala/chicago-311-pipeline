"""Extract: pull 311 requests from the Chicago Data Portal, or generate a sample."""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Iterator, Optional

import pandas as pd
import requests

from . import config


def fetch_api(since: Optional[str] = None, max_rows: Optional[int] = None) -> Iterator[pd.DataFrame]:
    """Yield DataFrames page by page. `since` is an ISO timestamp watermark: only
    records modified after it are requested (incremental extraction)."""
    headers = {"X-App-Token": config.SOCRATA_APP_TOKEN} if config.SOCRATA_APP_TOKEN else {}
    offset, fetched = 0, 0
    while True:
        params = {
            "$select": ",".join(config.RAW_COLUMNS),
            "$order": "last_modified_date ASC, sr_number ASC",
            "$limit": config.PAGE_SIZE,
            "$offset": offset,
        }
        if since:
            params["$where"] = f"last_modified_date > '{since}'"
        resp = requests.get(config.SOCRATA_URL, params=params, headers=headers, timeout=60)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return
        df = pd.DataFrame(rows).reindex(columns=config.RAW_COLUMNS)
        yield df
        fetched += len(df)
        offset += config.PAGE_SIZE
        if max_rows and fetched >= max_rows:
            return


_TYPES = [
    ("Pothole in Street", "PHF", "Dept of Streets & Sanitation", 3.5),
    ("Graffiti Removal Request", "GRAF", "Dept of Streets & Sanitation", 5.0),
    ("Rodent Baiting/Rat Complaint", "SGG", "Dept of Streets & Sanitation", 7.0),
    ("Street Light Out Complaint", "SFC", "Dept of Transportation", 9.0),
    ("Garbage Cart Black Maintenance/Replacement", "SGQ", "Dept of Streets & Sanitation", 12.0),
    ("Building Violation", "BBK", "Dept of Buildings", 30.0),
    ("Abandoned Vehicle Complaint", "ABV", "Chicago Police Department", 6.0),
]


def generate_sample(n: int = 20_000, seed: int = 42, start: str = "2024-01-01") -> pd.DataFrame:
    """Deterministic synthetic data with the same schema as the API. Used for offline
    runs, tests and CI. Includes a few intentional duplicates and open tickets."""
    rng = random.Random(seed)
    base = datetime.fromisoformat(start)
    rows = []
    for i in range(n):
        t = rng.choice(_TYPES)
        created = base + timedelta(minutes=rng.randint(0, 60 * 24 * 365))
        is_open = rng.random() < 0.08
        hours = max(0.5, rng.lognormvariate(0, 0.9) * t[3])
        closed = None if is_open else created + timedelta(hours=hours)
        modified = closed or created + timedelta(hours=rng.randint(1, 48))
        ward = rng.randint(1, 50)
        rows.append({
            "sr_number": f"SR{24000000 + i}",
            "sr_type": t[0], "sr_short_code": t[1], "owner_department": t[2],
            "status": "Open" if is_open else "Completed",
            "origin": rng.choice(["Phone Call", "Mobile Device", "Web Portal", "Email"]),
            "created_date": created.isoformat(timespec="milliseconds"),
            "last_modified_date": modified.isoformat(timespec="milliseconds"),
            "closed_date": closed.isoformat(timespec="milliseconds") if closed else None,
            "zip_code": str(60601 + rng.randint(0, 60)),
            "community_area": str(rng.randint(1, 77)),
            "ward": str(ward),
            "latitude": str(round(41.65 + rng.random() * 0.35, 6)),
            "longitude": str(round(-87.9 + rng.random() * 0.35, 6)),
        })
    df = pd.DataFrame(rows)
    # inject duplicate rows (older versions of the same ticket) to exercise dedup logic
    dupes = df.sample(frac=0.01, random_state=seed).copy()
    dupes["status"] = "Open"
    dupes["closed_date"] = None
    dupes["last_modified_date"] = dupes["created_date"]
    return pd.concat([df, dupes], ignore_index=True)
