import json
from pathlib import Path

import psycopg2
from locust import events

import globals as G
from locust_base import BenchmarkUser
from server.req_sql import execute

CATALOG_PATH = Path(__file__).parent.parent / "catalog_cache.json"
with open(CATALOG_PATH) as f:
    CATALOG: list[dict] = json.load(f)


class SQLUser(BenchmarkUser):
    def on_start(self):
        try:
            self.conn = psycopg2.connect(**G.POSTGRES)
            self.cur  = self.conn.cursor()
            self.catalog = CATALOG
        except Exception as e:
            events.request.fire(
                request_type="DB",
                name="connect",
                response_time=0,
                response_length=0,
                exception=e,
            )
            raise

    def on_stop(self):
        self.cur.close()
        self.conn.close()

    def execute_op(self, req):
        try:
            return execute(self.conn, self.cur, req)
        except Exception:
            self.conn.rollback()
            raise
