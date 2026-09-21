"""CLI entry point:  python -m pipeline.run --source sample|api [--full-refresh]"""
from __future__ import annotations

import argparse
from pathlib import Path
import logging
import time

from . import config, extract, load, quality, transform

log = logging.getLogger("pipeline")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Chicago 311 ELT pipeline")
    p.add_argument("--source", choices=["api", "sample"], default="sample")
    p.add_argument("--max-rows", type=int, default=None, help="cap rows pulled from the API")
    p.add_argument("--sample-size", type=int, default=20_000)
    p.add_argument("--full-refresh", action="store_true", help="ignore watermark, reload everything")
    p.add_argument("--db", default=None)
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    t0 = time.time()
    con = load.connect(Path(args.db) if args.db else None)
    if args.full_refresh:
        con.execute("DELETE FROM raw_requests")

    inserted = 0
    if args.source == "sample":
        inserted = load.upsert_raw(con, extract.generate_sample(args.sample_size))
    else:
        watermark = load.get_watermark(con)
        log.info("incremental extract since watermark=%s", watermark)
        for page in extract.fetch_api(since=watermark, max_rows=args.max_rows):
            inserted += load.upsert_raw(con, page)
    log.info("loaded %d new raw rows", inserted)

    built = transform.run_models(con)
    log.info("built models: %s", ", ".join(built))

    checks = quality.run_checks(con)
    for c in checks:
        log.info("[%s] %s - %s", "PASS" if c.passed else "FAIL", c.name, c.detail)
    quality.assert_passed(checks)

    log.info("done in %.1fs", time.time() - t0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
