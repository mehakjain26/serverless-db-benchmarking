import globals as G
from locust_base import BenchmarkHttpUser
from server.req_sql import sample_catalog

import psycopg2


class SQLHttpUser(BenchmarkHttpUser):
    def on_start(self):
        conn = psycopg2.connect(**G.POSTGRES)
        cur = conn.cursor()
        self.catalog = sample_catalog(cur, G.TRANSPORT_ID)
        cur.close()
        conn.close()
