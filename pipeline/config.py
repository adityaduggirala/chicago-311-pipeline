"""Central configuration. Override with environment variables."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("PIPELINE_DB", ROOT / "data" / "warehouse.duckdb"))
SQL_DIR = ROOT / "sql"

# Chicago Data Portal (Socrata) - "311 Service Requests"
SOCRATA_URL = os.getenv(
    "SOCRATA_URL", "https://data.cityofchicago.org/resource/v6vf-nfxy.json"
)
SOCRATA_APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN")  # optional, raises rate limits
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "5000"))

# Columns we pull from the API (keeps payloads small).
RAW_COLUMNS = [
    "sr_number", "sr_type", "sr_short_code", "owner_department", "status",
    "origin", "created_date", "last_modified_date", "closed_date",
    "zip_code", "community_area", "ward", "latitude", "longitude",
]
