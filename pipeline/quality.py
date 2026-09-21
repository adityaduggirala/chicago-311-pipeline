"""Data-quality gates. Each check returns (name, passed, detail). The pipeline fails
loudly if a blocking check fails, so bad data never reaches the marts."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def _scalar(con, sql):
    return con.execute(sql).fetchone()[0]


def run_checks(con) -> list[Check]:
    checks: list[Check] = []

    n = _scalar(con, "SELECT count(*) FROM stg_requests")
    checks.append(Check("staging_not_empty", n > 0, f"{n} rows"))

    nulls = _scalar(con, "SELECT count(*) FROM stg_requests WHERE sr_number IS NULL OR created_at IS NULL")
    checks.append(Check("keys_not_null", nulls == 0, f"{nulls} rows missing sr_number/created_at"))

    dupes = _scalar(con, "SELECT count(*) - count(DISTINCT sr_number) FROM stg_requests")
    checks.append(Check("sr_number_unique", dupes == 0, f"{dupes} duplicate sr_number"))

    bad_time = _scalar(con, "SELECT count(*) FROM stg_requests WHERE closed_at < created_at")
    checks.append(Check("closed_after_created", bad_time == 0, f"{bad_time} rows closed before created"))

    bad_status = _scalar(
        con,
        "SELECT count(*) FROM stg_requests WHERE status NOT IN ('Open','Completed','Canceled')",
    )
    checks.append(Check("status_accepted_values", bad_status == 0, f"{bad_status} unexpected statuses"))

    bad_geo = _scalar(
        con,
        "SELECT count(*) FROM stg_requests WHERE latitude IS NOT NULL AND "
        "(latitude NOT BETWEEN 41.6 AND 42.1 OR longitude NOT BETWEEN -88.0 AND -87.5)",
    )
    total_geo = max(_scalar(con, "SELECT count(*) FROM stg_requests WHERE latitude IS NOT NULL"), 1)
    # warn-level: allow up to 1% outside Chicago bounds
    checks.append(Check("geo_within_chicago", bad_geo / total_geo <= 0.01, f"{bad_geo}/{total_geo} outside bounds"))

    return checks


def assert_passed(checks: list[Check]) -> None:
    failed = [c for c in checks if not c.passed]
    if failed:
        raise RuntimeError("Data quality failed: " + "; ".join(f"{c.name} ({c.detail})" for c in failed))
