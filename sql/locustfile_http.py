import json
from pathlib import Path
from locust import events
import globals as G
from locust_base import BenchmarkHttpUser

CATALOG_PATH = Path(__file__).parent.parent / "catalog_cache.json"

try:
    with open(CATALOG_PATH) as f:
        CATALOG: list[dict] = json.load(f)
except FileNotFoundError:
    CATALOG = []
    print(f"WARNING: {CATALOG_PATH} not found. Catalog will be empty.")

class SQLHttpUser(BenchmarkHttpUser):
    def on_start(self):
        if not CATALOG:
            # Fallback for local testing if cache is missing
            import psycopg2
            from server import db_config as SG
            from server.req_sql import sample_catalog
            
            try:
                conn = psycopg2.connect(**SG.POSTGRES)
                cur = conn.cursor()
                self.catalog = sample_catalog(cur, G.TRANSPORT_ID)
                cur.close()
                conn.close()
            except Exception as e:
                events.request.fire(
                    request_type="DB",
                    name="catalog_bootstrap",
                    response_time=0,
                    response_length=0,
                    exception=e,
                )
        else:
            self.catalog = CATALOG
