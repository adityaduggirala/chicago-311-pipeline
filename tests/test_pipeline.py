import pytest

from pipeline import extract, load, quality, transform


@pytest.fixture()
def con():
    import duckdb
    c = duckdb.connect(":memory:")
    c.execute(load.RAW_DDL)
    yield c
    c.close()


def _build(con, n=2000):
    load.upsert_raw(con, extract.generate_sample(n, seed=1))
    transform.run_models(con)


def test_models_build_and_quality_passes(con):
    _build(con)
    checks = quality.run_checks(con)
    assert all(c.passed for c in checks), [c for c in checks if not c.passed]


def test_load_is_idempotent(con):
    df = extract.generate_sample(500, seed=2)
    first = load.upsert_raw(con, df)
    second = load.upsert_raw(con, df)
    assert first > 0 and second == 0


def test_dedup_keeps_latest_version(con):
    _build(con, 1000)
    raw_rows = con.execute("SELECT count(*) FROM raw_requests").fetchone()[0]
    stg_rows = con.execute("SELECT count(*) FROM stg_requests").fetchone()[0]
    assert stg_rows < raw_rows  # sample injects older duplicate versions
    open_but_closed = con.execute(
        "SELECT count(*) FROM stg_requests WHERE status='Open' AND closed_at IS NOT NULL"
    ).fetchone()[0]
    assert open_but_closed == 0


def test_quality_gate_catches_bad_data(con):
    _build(con, 500)
    con.execute("UPDATE stg_requests SET closed_at = created_at - INTERVAL 1 DAY WHERE sr_number = (SELECT min(sr_number) FROM stg_requests WHERE closed_at IS NOT NULL)")
    with pytest.raises(RuntimeError):
        quality.assert_passed(quality.run_checks(con))


def test_marts_have_expected_shape(con):
    _build(con)
    assert con.execute("SELECT count(*) FROM mart_ward_backlog").fetchone()[0] <= 50
    p = con.execute("SELECT min(p90_hours - median_hours) FROM mart_resolution_by_type").fetchone()[0]
    assert p >= 0
    # window-function mart: first row's rolling avg equals its own count
    r = con.execute("SELECT requests, rolling_7d_avg FROM mart_volume_trend ORDER BY created_date LIMIT 1").fetchone()
    assert r[0] == r[1]
