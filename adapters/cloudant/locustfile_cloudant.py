import json
from pathlib import Path

from locust import events

from core import BenchmarkUser
from database_clients.req_cloudant import execute, get_client

CATALOG_PATH = Path(__file__).parent.parent.parent / "core" / "catalog_cache.json"
with open(CATALOG_PATH) as f:
    CATALOG: list[dict] = json.load(f)


class CloudantUser(BenchmarkUser):
    def on_start(self):
        try:
            self._client = get_client()
            self.catalog = CATALOG
        except Exception as e:
            events.request.fire(
                request_type="DB", name="connect",
                response_time=0, response_length=0, exception=e,
            )
            raise

    def execute_op(self, req):
        return execute(self._client, req)
