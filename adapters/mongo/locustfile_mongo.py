import json
from pathlib import Path

from locust import events

from core import globals as G
from core import BenchmarkUser
from database_clients.req_mongo import execute, get_client, get_col

CATALOG_PATH = Path(__file__).parent.parent.parent / "core" / "catalog_cache.json"
with open(CATALOG_PATH) as f:
    CATALOG: list[dict] = json.load(f)


class MongoUser(BenchmarkUser):
    def on_start(self):
        try:
            self._client = get_client()
            self.col = get_col(self._client)
            self.catalog = CATALOG
        except Exception as e:
            events.request.fire(
                request_type="DB", name="connect",
                response_time=0, response_length=0, exception=e,
            )
            raise

    def on_stop(self):
        self._client.close()

    def execute_op(self, req):
        return execute(self.col, req)
