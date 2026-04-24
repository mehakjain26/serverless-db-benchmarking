import json
from pathlib import Path

from locust_base import BenchmarkHttpUser

CATALOG_PATH = Path(__file__).parent.parent / "catalog_cache.json"
with open(CATALOG_PATH) as f:
    CATALOG: list[dict] = json.load(f)


class CloudantHttpUser(BenchmarkHttpUser):
    def on_start(self):
        self.catalog = CATALOG
