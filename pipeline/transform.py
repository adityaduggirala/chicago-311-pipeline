"""Transform: run numbered SQL model files in order (a tiny dbt-style runner)."""
from __future__ import annotations

from . import config


def run_models(con, sql_dir=None) -> list[str]:
    sql_dir = sql_dir or config.SQL_DIR
    built = []
    for path in sorted(sql_dir.glob("*.sql")):
        con.execute(path.read_text())
        built.append(path.stem)
    return built
